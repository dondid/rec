"""Lossless pre-TTS partitions. Estimates are never acoustic word times."""
import math
from pathlib import Path
import re

from .core import key, now, read, sha, write


def split(source, output, parts=None, target=None, chapters=False, delimiter=None,
          manual=None, semantic=False, wpm=150):
    source=Path(source).resolve(); output=Path(output).resolve()
    if output.exists():raise ValueError('Director existent; alege o destinație nouă.')
    if sum([parts is not None,target is not None,chapters or delimiter is not None,manual is not None,semantic])!=1:
        raise ValueError('Alege exact o metodă de split text.')
    if not math.isfinite(wpm) or wpm<=0:raise ValueError('WPM trebuie să fie pozitiv și finit.')
    raw=source.read_bytes(); text=raw.decode('utf-8-sig')
    if not text.strip():raise ValueError('Text gol.')
    # Boundaries include whitespace in the preceding part, preserving every character.
    boundaries=sorted({0,len(text),*[m.end() for m in re.finditer(r'(?<=[.!?…])(?:[”»\x22\x27)]*)\s+|\n[ \t]*\n',text)]})
    if manual:
        ranges=read(manual)['ranges']; cursor=0
        for a,b in ranges:
            if type(a) is not int or type(b) is not int or a!=cursor or not a<b<=len(text):raise ValueError('Intervalele trebuie să formeze o partiție completă, în caractere Unicode.')
            if 0<b<len(text) and text[b-1].isalnum() and text[b].isalnum():raise ValueError('Limita manuală taie un cuvânt.')
            cursor=b
        if cursor!=len(text):raise ValueError('Intervalele nu acoperă tot textul.')
        bounds=[0]+[b for a,b in ranges];method='manual'
    elif chapters or delimiter is not None:
        if delimiter is not None:
            if not delimiter:raise ValueError('Delimitator gol.')
            cuts=[m.start() for m in re.finditer(re.escape(delimiter),text)]
        else:cuts=[m.start() for m in re.finditer(r'(?mi)^(?:#{1,6}\s+|(?:capitol(?:ul)?|chapter)\s+\S)',text)]
        bounds=sorted({0,len(text),*cuts});method='chapters'
        if len(bounds)<3:raise ValueError('Nu există suficiente capitole/delimitatoare explicite.')
    elif semantic:
        # Local lexical cohesion proposal, not an AI understanding claim.
        paragraphs=[0]+[m.end() for m in re.finditer(r'\n[ \t]*\n',text)]+[len(text)]
        cuts=[]
        for i in range(1,len(paragraphs)-1):
            a=set(re.findall(r'\w{4,}',text[paragraphs[i-1]:paragraphs[i]].casefold()))
            b=set(re.findall(r'\w{4,}',text[paragraphs[i]:paragraphs[i+1]].casefold()))
            similarity=len(a&b)/max(1,len(a|b))
            if similarity<.12:cuts.append(paragraphs[i])
        bounds=sorted({0,len(text),*cuts});method='lexical_paragraph_proposal'
    else:
        if target is not None:
            if not math.isfinite(target) or target<=0:raise ValueError('Durata țintă trebuie să fie pozitivă și finită.')
            parts=max(1,math.ceil(len(text.split())*60/wpm/target))
        if type(parts) is not int or not 1<=parts<=1000:raise ValueError('Numărul de părți trebuie să fie 1–1000.')
        if parts>len(boundaries)-1:raise ValueError('Prea puține propoziții/paragrafe pentru numărul de părți; furnizează intervale manuale.')
        # Weights are lexical word counts; leave enough safe boundaries for remaining parts.
        counts=[len(text[:b].split()) for b in boundaries]; total=counts[-1]; bounds=[0];last=0
        for i in range(1,parts):
            options=range(last+1,len(boundaries)-(parts-i))
            selected=min(options,key=lambda j:abs(counts[j]-total*i/parts))
            bounds.append(boundaries[selected]);last=selected
        bounds.append(len(text));method='estimated_duration' if target is not None else 'balanced_sentences'
    chunks=[]
    for i,(a,b) in enumerate(zip(bounds,bounds[1:]),1):
        chunk=text[a:b]
        if not chunk.strip():raise ValueError('Parte fără conținut; ajustează limitele.')
        chunks.append(dict(id=f'part-{i:03d}',path=f'part-{i:03d}.txt',start=a,end=b,
                           byte_start=len(text[:a].encode('utf-8'))+(3 if raw.startswith(b'\xef\xbb\xbf') else 0),
                           byte_end=len(text[:b].encode('utf-8'))+(3 if raw.startswith(b'\xef\xbb\xbf') else 0),
                           text_sha256=key(chunk),estimated_seconds=len(chunk.split())*60/wpm))
    output.mkdir(parents=True)
    for item in chunks:(output/item['path']).write_bytes(text[item['start']:item['end']].encode('utf-8'))
    result=dict(schema_version=1,kind='text_partition',created_utc=now(),source=str(source),source_sha256=sha(source),
                encoding='utf-8-sig' if raw.startswith(b'\xef\xbb\xbf') else 'utf-8',offset_unit='unicode_codepoint',method=method,
                wpm=wpm,duration_status='estimated_before_synthesis',semantic_status='proposal_requires_review' if semantic else 'not_used',
                parts=chunks,technical_status='passed')
    write(output/'text-parts.json',result)
    return dict(result,manifest=str(output/'text-parts.json'))


def merge(manifest,output):
    manifest=Path(manifest).resolve(); output=Path(output)
    if output.exists():raise ValueError('Text destinație existent.')
    plan=read(manifest); chunks=[]
    for item in plan['parts']:
        chunk=(manifest.parent/item['path']).read_bytes().decode('utf-8')
        if key(chunk)!=item['text_sha256']:raise ValueError('Parte modificată; reunirea fidelă nu poate fi confirmată.')
        chunks.append(chunk)
    raw=''.join(chunks).encode(plan['encoding'])
    import hashlib
    if hashlib.sha256(raw).hexdigest()!=plan['source_sha256']:raise ValueError('Reunirea nu reconstruiește sursa.')
    output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(raw)
    return dict(output=str(output.resolve()),sha256=sha(output),technical_status='passed')
