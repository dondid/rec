import json
import pytest
from rec_tts.text import normalize, read_text, segment, sentence_ends, replace_literals, rules_from, prepare
from rec_tts.cli import validate_config
from rec_tts.common import ROOT
from rec_tts.cache import cache_key


def config():
    return json.loads((ROOT / 'rec.json').read_text())


def test_utf8_bom_crlf_sedilla_spaces(tmp_path):
    path = tmp_path / 'Cuvinte cu diacritice ș.txt'
    path.write_bytes('\ufeff  Ştiinţă  şi\tpace.\r\nAici!\r\n\r\nŢară.  '.encode())
    assert read_text(path) == 'Știință și pace. Aici!\n\nȚară.'
    assert normalize('s\u0326i') == 'și'


@pytest.mark.parametrize('raw', [b'\xff', b'', b'  \r\n '])
def test_invalid_or_empty(tmp_path, raw):
    p = tmp_path / 'text.txt'
    p.write_bytes(raw)
    with pytest.raises(ValueError):
        read_text(p)


def test_abbreviations_decimals_initials_urls():
    text = 'Dl. I. Popescu și dr. Ion au nr. 12,5. Vezi https://exemplu.ro/test. Acum?' 
    ends = sentence_ends(text)
    assert len(ends) == 3
    assert text[:ends[0]] == 'Dl. I. Popescu și dr. Ion au nr. 12,5.'
    assert sentence_ends('Avem 12.5 lei. Da!') == [14, 18]


@pytest.mark.parametrize('maximum', [30, 50, 120, 500])
def test_reconstruction(maximum):
    text = normalize(('Ana merge repede, vede copaci; dr. Ion așteaptă. Oare vine?\n\n' * 30) + 'Sfârșit!')
    parts = segment(text, min(25, maximum), maximum)
    assert ''.join(s['text'] + s['separator'] for s in parts) == text
    assert all(text[s['start']:s['end']] == s['text'] for s in parts)
    assert all(len(s['text']) <= maximum for s in parts)
    assert sum(s['boundary'] == 'paragraph' for s in parts) == 30


def test_indivisible_token():
    with pytest.raises(ValueError, match='Token indivizibil'):
        segment('x' * 501)


def test_literal_longest_no_cascade():
    rules = [{'match': 'API', 'say': 'B', 'whole_word': True},
             {'match': 'API mare', 'say': 'C', 'whole_word': True},
             {'match': 'B', 'say': 'D', 'whole_word': True}]
    text, changes = replace_literals('API mare API XAPI B', rules)
    assert text == 'C B XAPI D'
    assert len(changes) == 3
    assert replace_literals('12,5% API', [{'match': '12,5%', 'say': 'număr', 'whole_word': False}])[0] == 'număr API'


@pytest.mark.parametrize('value', [0.79, 1.21, float('nan'), float('inf'), '1', True])
def test_speed_validation(value):
    c = config()
    c['speed'] = value
    with pytest.raises(ValueError):
        validate_config(c)


@pytest.mark.parametrize('key,value', [('channels', 2), ('segment_max_chars', 0), ('segment_target_chars', 1000),
                                      ('sentence_gap_ms', -1), ('mp3_bitrate', '999k'), ('engine', 'cloud')])
def test_other_validation(key, value):
    c = config()
    c[key] = value
    with pytest.raises(ValueError):
        validate_config(c)


def test_cache_identity():
    engine = {'speed': 1.0, 'model': 'abc', 'adapter': 1}
    key = cache_key('Același text.', engine)
    assert key == cache_key('Același text.', dict(reversed(list(engine.items()))))
    assert key != cache_key('Alt text.', engine)
    for field in engine:
        assert key != cache_key('Același text.', dict(engine, **{field: 'changed'}))


def test_preview_safe_end(tmp_path):
    p = tmp_path / 'text.txt'
    p.write_text('Prima frază are cinci cuvinte. A doua este aici.\n\nUltima frază.', encoding='utf-8')
    data = prepare(p, [], 300, 500, words=2)
    assert data['normalized'] == 'Prima frază are cinci cuvinte.'
    assert data['partial_preview']


def test_pronunciation_rules_validation(tmp_path):
    p = tmp_path / 'rules.json'
    for invalid in ({}, [{'match': '', 'say': 'x'}], [{'match': 'x', 'say': ''}], [{'match': 'x', 'say': 'y', 'whole_word': 'yes'}]):
        p.write_text(json.dumps(invalid))
        with pytest.raises(ValueError):
            rules_from(p)
