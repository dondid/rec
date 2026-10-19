"""Lossless segmentation of normalized Romanian text; offsets use Unicode characters."""
import json
import re
import unicodedata
from pathlib import Path


def normalize(raw):
    text = unicodedata.normalize('NFC', raw.lstrip('\ufeff')).translate(str.maketrans('şţŞŢ', 'șțȘȚ'))
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    paragraphs = re.split(r'\n[ \t]*\n+', text)
    return '\n\n'.join(re.sub(r'\s+', ' ', p).strip() for p in paragraphs if p.strip())


def read_text(path):
    if Path(path).suffix.lower() != '.txt':
        raise ValueError('Inputul trebuie să fie .txt UTF-8.')
    try:
        text = normalize(Path(path).read_text(encoding='utf-8-sig'))
    except UnicodeDecodeError as e:
        raise ValueError(f'Codare UTF-8 invalidă: {path}: {e}') from e
    if not text:
        raise ValueError('Input gol după normalizare.')
    return text


def rules_from(path):
    rules = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(rules, list):
        raise ValueError('Dicționarul trebuie să fie o listă JSON.')
    for r in rules:
        if (not isinstance(r, dict) or not isinstance(r.get('match'), str)
                or not r['match'] or not isinstance(r.get('say'), str) or not r['say'].strip()
                or type(r.get('whole_word', True)) is not bool):
            raise ValueError('Regulă de pronunție invalidă.')
    return rules


def replace_literals(text, rules):
    ordered = sorted(enumerate(rules), key=lambda x: -len(x[1]['match']))
    patterns = []
    for _, r in ordered:
        p = re.escape(r['match'])
        patterns.append(('(?<!\\w)' + p + '(?!\\w)') if r.get('whole_word', True) else p)
    changes = []
    if not patterns:
        return text, changes
    regex = re.compile('|'.join('(' + p + ')' for p in patterns))
    def substitute(m):
        r = ordered[m.lastindex - 1][1]
        changes.append({'start': m.start(), 'end': m.end(), 'match': m.group(), 'say': r['say']})
        return r['say']
    return regex.sub(substitute, text), changes


def sentence_ends(text):
    """Return sentence boundaries, protecting common abbreviations, initials, URLs, decimals."""
    ends = []
    for m in re.finditer(r'[.!?]+[”»"\')\]]*(?=\s|$)', text):
        end = m.end()
        prefix = text[:m.start() + 1]
        token = re.search(r'\S+$', prefix)
        token = token.group() if token else ''
        if m.group().startswith('.'):
            if re.search(r'(?i)\b(?:dl|dna|d-na|dr|prof|nr|etc|str|ing|ș.a|ș.m.d)\.$', prefix):
                continue
            if re.search(r'\b[A-ZĂÂÎȘȚ]\.$', prefix):
                continue
        ends.append(end)
    if not ends or ends[-1] != len(text):
        ends.append(len(text))
    return ends


def segment(text, target=300, maximum=500):
    segments = []
    offset = 0
    paragraphs = text.split('\n\n')
    for paragraph, p in enumerate(paragraphs):
        ends = set(sentence_ends(p))
        start = 0
        while start < len(p):
            limit = min(start + maximum, len(p))
            candidates = [e for e in ends if start < e <= limit]
            if candidates:
                near = [e for e in candidates if e - start >= target]
                end = min(near) if near else max(candidates)
            elif limit == len(p):
                end = limit
            else:
                punctuation = [m.end() for m in re.finditer(r'[,;:—](?=\s)', p[start:limit])]
                if punctuation:
                    end = start + punctuation[-1]
                else:
                    end = p.rfind(' ', start, limit + 1)
                    if end <= start:
                        raise ValueError(f'Token indivizibil peste {maximum} caractere, offset {offset + start}.')
            next_start = end
            while next_start < len(p) and p[next_start].isspace():
                next_start += 1
            boundary = 'sentence' if end in ends else 'technical'
            separator = p[end:next_start]
            if end == len(p):
                boundary = 'paragraph' if paragraph < len(paragraphs) - 1 else 'end'
                separator = '\n\n' if boundary == 'paragraph' else ''
            segments.append({'index': len(segments), 'paragraph': paragraph, 'start': offset + start,
                             'end': offset + end, 'text': p[start:end], 'separator': separator,
                             'boundary': boundary})
            start = next_start
        offset += len(p) + 2
    assert ''.join(s['text'] + s['separator'] for s in segments) == text
    return segments


def prepare(path, rules, target, maximum, words=None):
    normalized = read_text(path)
    partial = words is not None
    if words:
        tokens = list(re.finditer(r'\S+', normalized))
        if len(tokens) > words:
            cutoff = tokens[words - 1].end()
            end = next(e for e in sentence_ends(normalized) if e >= cutoff)
            normalized = normalized[:end].rstrip()
    segments = segment(normalized, target, maximum)
    changes = []
    for s in segments:
        s['spoken'], log = replace_literals(s['text'], rules)
        # Replacements must obey the same engine memory limit.
        if any(len(t) > maximum for t in s['spoken'].split()):
            raise ValueError(f'Pronunție cu token peste limită, segment {s["index"]}.')
        changes.extend(dict(c, segment=s['index']) for c in log)
    warnings = [{'offset': m.start(), 'value': m.group(), 'reason': 'Lectură contextuală de verificat'}
                for m in re.finditer(r'https?://\S+|\b\d[\d.,:/%°-]*\w*|\b[A-ZĂÂÎȘȚ]{2,}\b', normalized)]
    return {'normalized': normalized, 'segments': segments, 'replacements': changes,
            'warnings': warnings, 'partial_preview': partial}
