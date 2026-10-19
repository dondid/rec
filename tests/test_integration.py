"""Real model/FFmpeg checks. Run explicitly: pytest -m integration.
Tests with mocks are in test_pipeline.py, not counted as real synthesis.
"""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
import uuid

import pytest

from rec_tts.common import ROOT, file_hash
from rec_tts.text import read_text

pytestmark = pytest.mark.integration
TTS = ROOT / 'tts'


@pytest.fixture(autouse=True)
def prerequisites():
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        pytest.skip('FFmpeg/ffprobe lipsă: integrarea audio nu poate fi executată.')
    if not (ROOT / 'models/piper/model.lock.json').exists():
        pytest.skip('Model local lipsă.')


def invoke(*args, ok=True, **kwargs):
    p = subprocess.run([str(TTS), *map(str, args)], capture_output=True, text=True, **kwargs)
    if ok:
        assert p.returncode == 0, p.stderr
        return json.loads(p.stdout)
    assert p.returncode != 0
    return p


def test_short_paths_and_full_decode(tmp_path):
    source = tmp_path / 'Română și spații $ „citate”.txt'
    source.write_text('Ștefan merge la Iași. Oare ajunge înainte de ploaie?\n\nMăriuca îl așteaptă la poartă.', encoding='utf-8')
    destination = tmp_path / 'Rezultat cu diacritice ș $.mp3'
    result = invoke('render', source, '-o', destination, '--keep-wav', cwd='/tmp')
    assert result['segments_completed'] == result['segments_expected'] == 2
    assert destination.with_suffix('.wav').exists()
    verified = invoke('verify', destination)
    assert verified['full_decode'] and verified['accepted']
    invoke('render', source, '-o', destination, '--keep-wav', ok=False)  # WAV overwrite protected
    assert invoke('render', source, '-o', destination, '--keep-wav', '--force')['cache_hits'] == 2
    assert result['listening_status'] == 'not_listened'
    assert source.read_text().startswith('Ștefan')


def test_real_resume_corruption_bitrate_paragraph(tmp_path):
    source = tmp_path / 'reluare.txt'
    nonce = uuid.uuid4().hex[:8]
    paragraphs = [f'Proba {nonce}, capitolul {i}: Ascultăm frunzele și pașii de pe alee.' for i in range(6)]
    source.write_text('\n\n'.join(paragraphs), encoding='utf-8')
    output = tmp_path / 'reluare.mp3'
    before_runs = set((ROOT / 'work/runs').iterdir())
    with (tmp_path / 'stderr.log').open('w') as err, (tmp_path / 'stdout.log').open('w') as out:
        proc = subprocess.Popen([str(TTS), 'render', str(source), '-o', str(output), '--verbose'], stdout=out, stderr=err)
        deadline = time.monotonic() + 120
        manifest = None
        try:
            while time.monotonic() < deadline and proc.poll() is None:
                for directory in set((ROOT / 'work/runs').iterdir()) - before_runs:
                    p = directory / 'manifest.json'
                    try:
                        m = json.loads(p.read_text())
                        if m['completed'] >= 2:
                            manifest = m
                            proc.send_signal(signal.SIGINT)
                            break
                    except (FileNotFoundError, json.JSONDecodeError):
                        pass
                if manifest:
                    break
                time.sleep(0.05)
            proc.wait(timeout=60)
        finally:
            if proc.poll() is None:
                proc.kill()
        assert manifest is not None, 'Nu s-a observat un checkpoint.'
        assert proc.returncode == 130, (tmp_path / 'stderr.log').read_text()
    assert not output.exists()
    done = [s for s in manifest['segments'] if s.get('state') == 'complete']
    snapshots = {s['cache_key']: (file_hash(ROOT / 'work/cache' / (s['cache_key'] + '.wav')),
                                (ROOT / 'work/cache' / (s['cache_key'] + '.wav')).stat().st_mtime_ns)
                 for s in done}
    result = invoke('render', source, '-o', output)
    for key, state in snapshots.items():
        p = ROOT / 'work/cache' / (key + '.wav')
        assert (file_hash(p), p.stat().st_mtime_ns) == state
    assert result['cache_hits'] >= len(done)
    m = json.loads(Path(result['manifest']).read_text())
    broken = ROOT / 'work/cache' / (m['segments'][0]['cache_key'] + '.wav')
    broken.write_bytes(b'corrupt')
    result = invoke('render', source, '-o', output, '--force')
    assert result['cache_hits'] == 5
    config = json.loads((ROOT / 'rec.json').read_text())
    config['mp3_bitrate'] = '96k'
    cfg = tmp_path / 'config.json'
    cfg.write_text(json.dumps(config))
    result = invoke('--config', cfg, 'render', source, '-o', output, '--force')
    assert result['cache_hits'] == 6
    paragraphs[2] = f'Capitol schimbat {nonce}: O propoziție complet diferită.'
    source.write_text('\n\n'.join(paragraphs), encoding='utf-8')
    result = invoke('render', source, '-o', output, '--force')
    assert result['cache_hits'] == 5
    invoke('render', source, '-o', output, '--speed', '0.95', ok=False)
    assert invoke('render', source, '-o', output)['already_complete']


@pytest.mark.slow
def test_long_50000():
    source = ROOT / 'samples/long_ro.txt'
    assert len(read_text(source)) >= 50000
    destination = ROOT / 'output/test_lung.mp3'
    result = invoke('render', source, '-o', destination)
    m = json.loads(Path(result['manifest']).read_text())
    assert ''.join(s['text'] + s['separator'] for s in m['segments']) == read_text(source)
    assert result['segments_expected'] == result['segments_completed']
    assert all(s['state'] == 'complete' for s in m['segments'])
    for marker in ('Marcator inițial', 'Marcator median', 'Marcator final'):
        assert marker in m['normalized']
    assert invoke('verify', destination)['full_decode']
    # Check duplicate paragraphs still occupy separate positions in assembled audio.
    assert len(m['segments']) > len(set(s['cache_key'] for s in m['segments']))


@pytest.mark.offline
def test_offline_namespace(tmp_path):
    check = subprocess.run(['unshare', '-Urn', 'true'], capture_output=True)
    if check.returncode:
        pytest.skip('Namespace de rețea indisponibil: ' + check.stderr.decode())
    source = tmp_path / 'offline.txt'
    source.write_text(f'Probă izolată {uuid.uuid4().hex}: În această zi, liniștea umple grădina.', encoding='utf-8')
    dest = tmp_path / 'offline.mp3'
    parent_namespace = os.readlink('/proc/self/ns/net')
    code = '''
import json, os, socket, subprocess, sys
namespace = os.readlink('/proc/self/ns/net')
assert namespace != sys.argv[1]
try:
    with socket.create_connection(('1.1.1.1', 443), timeout=1):
        raise RuntimeError('Conexiunea externă nu a fost blocată')
except OSError as error:
    blocked = str(error)
p = subprocess.run(sys.argv[2:], capture_output=True, text=True)
assert p.returncode == 0, p.stderr
result = json.loads(p.stdout)
result['network_isolation'] = {'parent': sys.argv[1], 'child': namespace, 'blocked_connection': blocked}
print(json.dumps(result))
'''
    p = subprocess.run(['unshare', '-Urn', str(ROOT / '.venv/bin/python'), '-c', code,
                        parent_namespace, str(TTS), 'render', str(source), '-o', str(dest)],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    result = json.loads(p.stdout)
    assert result['cache_hits'] == 0
    assert result['technical_status'] == 'passed'
    (ROOT / 'work/offline-evidence.json').write_text(json.dumps(result, indent=2))
    # Some kernels expose an empty route file instead of a header-only file.
    net = subprocess.run(['unshare', '-Urn', 'cat', '/proc/net/route'], capture_output=True, text=True)
    assert net.returncode == 0
    assert not [line for line in net.stdout.splitlines() if line.strip() and not line.startswith('Iface')]


def test_cli_invalid_input_and_real_ffmpeg_failure(tmp_path):
    bad = tmp_path / 'invalid.txt'
    output = tmp_path / 'audio.mp3'
    for content in (b'', b'\xff\xfeinvalid'):
        bad.write_bytes(content)
        p = invoke('render', bad, '-o', output, ok=False)
        assert 'gol' in p.stderr or 'UTF-8' in p.stderr
        assert not output.exists()
    source = ROOT / 'samples/test_ro.txt'
    invoke('render', source, '-o', output)
    original = file_hash(output)
    fake_bin = tmp_path / 'fake-bin'
    fake_bin.mkdir()
    fake = fake_bin / 'ffmpeg'
    fake.write_text('#!/bin/sh\nprintf "FFmpeg failure injected\\n" >&2\nexit 17\n')
    fake.chmod(0o755)
    env = dict(os.environ, PATH=str(fake_bin) + os.pathsep + os.environ['PATH'])
    p = invoke('render', source, '-o', output, '--force', ok=False, env=env)
    assert '17' in p.stderr and 'FFmpeg failure injected' in p.stderr
    assert file_hash(output) == original


def test_actual_engine_missing_and_invalid_onnx(tmp_path):
    from rec_tts.common import write_json
    from rec_tts.engine import Engine, MODEL_DIR, VOICE
    with pytest.raises(ValueError, match='fetch-model'):
        Engine(tmp_path)
    shutil.copyfile(MODEL_DIR / (VOICE + '.onnx.json'), tmp_path / (VOICE + '.onnx.json'))
    (tmp_path / (VOICE + '.onnx')).write_bytes(b'invalid ONNX data')
    lock = {'files': {name: {'size': (tmp_path / name).stat().st_size, 'sha256': file_hash(tmp_path / name)}
                      for name in (VOICE + '.onnx', VOICE + '.onnx.json')}}
    write_json(tmp_path / 'model.lock.json', lock)
    with pytest.raises(Exception, match='(INVALID_PROTOBUF|Protobuf|protobuf|model)'):
        Engine(tmp_path)
