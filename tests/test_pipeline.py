import copy
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import soundfile as sf

from rec_tts import audio, cache, pipeline
from rec_tts.common import ROOT, file_hash, write_json
from rec_tts.engine import validate_model


@pytest.fixture
def local(tmp_path, monkeypatch):
    root = tmp_path / 'proiect țară'
    root.mkdir()
    (root / 'work').mkdir()
    cache_dir = root / 'work/cache'
    monkeypatch.setattr(pipeline, 'ROOT', root)
    real_synth = cache.synthesize
    monkeypatch.setattr(pipeline, 'valid_entry', lambda k, r: cache.valid_entry(k, r, cache_dir))
    monkeypatch.setattr(pipeline, 'synthesize', lambda k, e, t, s: real_synth(k, e, t, s, cache_dir))
    monkeypatch.setattr(pipeline, 'validate_model', lambda: ({'files': {'a.onnx': {'sha256': 'fake'}}}, {'audio': {'sample_rate': 22050}}))
    monkeypatch.setattr(pipeline, 'engine_identity', lambda l, s: {'engine': 'fake', 'speed': s})
    calls = []
    class Engine:
        sample_rate = 22050
        load_seconds = 0.01
        def chunks(self, text, speed):
            calls.append(text)
            yield np.sin(np.arange(22050) * 0.03).astype('float32') * 0.1
            yield np.sin(np.arange(11025) * 0.03).astype('float32') * 0.1
    monkeypatch.setattr(pipeline, 'Engine', Engine)
    real_assemble = audio.assemble
    monkeypatch.setattr(audio, 'assemble', lambda s, d, r, c: real_assemble(s, d, r, c, cache_dir))
    def export(master, temporary, rate, config):
        temporary.write_bytes(b'fake verified mp3')
        return {'verification': {'accepted': True}}
    monkeypatch.setattr(audio, 'export', export)
    monkeypatch.setattr(audio, 'verify', lambda *a: {'accepted': True})
    monkeypatch.setattr(audio, 'command', lambda *a: SimpleNamespace(stdout='test tool version\n'))
    source = root / 'Text cu spații și „ghilimele” $.txt'
    source.write_text('Paragraful întâi.\n\nAl doilea paragraf.\n\nParagraful întâi.', encoding='utf-8')
    config = json.loads((ROOT / 'rec.json').read_text())
    return SimpleNamespace(root=root, cache=cache_dir, calls=calls, source=source, output=root / 'ieșire $.mp3', config=config)


def run(local, **kwargs):
    return pipeline.render(local.source, local.output, local.config, [], **kwargs)


def test_resume_preserves_hashes_and_timestamps(local):
    def interrupt(count):
        if count == 2:
            raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        run(local, after_segment=interrupt)
    before = {p.name: (file_hash(p), p.stat().st_mtime_ns) for p in local.cache.glob('*.wav')}
    assert len(before) == 2 and not local.output.exists()
    result = run(local)
    assert result['cache_hits'] == 3
    assert len(local.calls) == 2
    assert before == {p.name: (file_hash(p), p.stat().st_mtime_ns) for p in local.cache.glob('*.wav')}
    manifests = [json.loads(p.read_text()) for p in (local.root / 'work/runs').glob('*/manifest.json')]
    assert sorted(m['state'] for m in manifests) == ['complete', 'interrupted']


def test_one_paragraph_changed_and_intentional_repetition(local):
    first = run(local)
    assert len(local.calls) == 2 and first['segments_completed'] == 3
    manifest = json.loads(Path(first['manifest']).read_text())
    assert manifest['segments'][0]['cache_key'] == manifest['segments'][2]['cache_key']
    master = Path(first['manifest']).parent / 'master.wav'
    assert sf.info(master).frames == 3 * 33075 + round(0.15 * 22050) * 3 + round(0.4 * 22050) * 2
    local.source.write_text('Paragraful întâi.\n\nAl doilea schimbat.\n\nParagraful întâi.', encoding='utf-8')
    result = run(local, force=True)
    assert result['cache_hits'] == 2 and len(local.calls) == 3


def test_bitrate_and_dictionary_do_not_invalidate_audio(local):
    run(local)
    local.config['mp3_bitrate'] = '96k'
    result = run(local, force=True)
    assert result['cache_hits'] == 3 and len(local.calls) == 2
    result = pipeline.render(local.source, local.output, local.config,
                             [{'match': 'absent', 'say': 'înlocuit'}], force=True)
    assert result['cache_hits'] == 3 and len(local.calls) == 2


def test_corrupt_cache_regenerated(local):
    run(local)
    corrupted = next(local.cache.glob('*.wav'))
    corrupted.write_bytes(b'corrupt')
    result = run(local, force=True)
    assert len(local.calls) == 3
    assert sf.info(corrupted).frames == 33075
    assert result['segments_completed'] == 3


def test_output_protection_and_exact_repeat(local):
    run(local)
    assert run(local)['already_complete']
    local.output.write_bytes(b'existing private output')
    with pytest.raises(ValueError, match='Destinație existentă'):
        run(local)
    assert local.output.read_bytes() == b'existing private output'
    run(local, force=True)
    assert len(local.calls) == 2


def test_ffmpeg_error_preserves_export_and_cache(local, monkeypatch):
    run(local)
    original = local.output.read_bytes()
    def fail(*args):
        raise ValueError('FFmpeg failure simulated')
    monkeypatch.setattr(audio, 'export', fail)
    with pytest.raises(ValueError, match='FFmpeg'):
        run(local, force=True)
    assert local.output.read_bytes() == original
    assert len(local.calls) == 2


def test_no_space_mock(local, monkeypatch):
    monkeypatch.setattr(pipeline.shutil, 'disk_usage', lambda p: SimpleNamespace(free=0))
    with pytest.raises(ValueError, match='Spațiu insuficient'):
        run(local)
    assert not local.output.exists() and not local.calls


def test_failed_segment_no_publication(local, monkeypatch):
    def fail(*args):
        raise ValueError('synthesis failed')
    monkeypatch.setattr(pipeline, 'synthesize', fail)
    with pytest.raises(ValueError):
        run(local)
    m = json.loads(next((local.root / 'work/runs').glob('*/manifest.json')).read_text())
    assert m['error']['segment'] == 0
    assert m['state'] == 'failed' and not local.output.exists()


def test_model_missing_corrupt(tmp_path):
    with pytest.raises(ValueError, match='Model lipsă'):
        validate_model(tmp_path)
    write_json(tmp_path / 'model.lock.json', {'files': {'ro_RO-mihai-medium.onnx': {'size': 4, 'sha256': 'bad'}}})
    (tmp_path / 'ro_RO-mihai-medium.onnx').write_bytes(b'1234')
    with pytest.raises(ValueError, match='Model corupt'):
        validate_model(tmp_path)


def test_audio_subprocess_failure(monkeypatch):
    monkeypatch.setattr(audio.subprocess, 'run', lambda *a, **kw: SimpleNamespace(returncode=1, stderr='failure'))
    with pytest.raises(ValueError, match='ffmpeg a eșuat'):
        audio.command(['ffmpeg'])


def test_nonfinite_rejected(tmp_path):
    class BadEngine:
        sample_rate = 22050
        def chunks(self, *args):
            yield np.array([np.nan], dtype='float32')
    with pytest.raises(ValueError, match='ne-finit'):
        cache.synthesize('bad', BadEngine(), 'text', 1, tmp_path)
    assert not cache.valid_entry('bad', 22050, tmp_path)


def test_expanded_pronunciation_is_bounded(tmp_path):
    calls = []
    class Engine:
        sample_rate = 22050
        def chunks(self, text, speed):
            calls.append(text)
            assert len(text) <= 500
            yield np.ones(100, dtype='float32') * 0.1
    spoken = 'cuvânt ' * 200 + 'final'
    key = cache.cache_key(spoken, {'voice': 'fake'})
    result = cache.synthesize(key, Engine(), spoken, 1, tmp_path)
    assert len(calls) > 1
    assert ''.join(calls).replace(' ', '') == spoken.replace(' ', '')
    assert result['boundary_types'][:-1] == ['technical'] * (len(calls) - 1)
    assert cache.valid_entry(key, 22050, tmp_path)
