"""The only synthesis adapter. Network access exists only in fetch_model()."""
import importlib.metadata
import json
import os
from pathlib import Path
import time

from .common import ROOT, file_hash, write_json

VOICE = 'ro_RO-mihai-medium'
MODEL_DIR = ROOT / 'models/piper'
ADAPTER_VERSION = 1


def validate_model(directory=MODEL_DIR):
    try:
        lock = json.loads((directory / 'model.lock.json').read_text())
        for name in (VOICE + '.onnx', VOICE + '.onnx.json'):
            item = lock['files'][name]
            path = directory / name
            if path.stat().st_size != item['size'] or file_hash(path) != item['sha256']:
                raise ValueError(f'Model corupt: {name}')
        config = json.loads((directory / (VOICE + '.onnx.json')).read_text())
        if config['audio']['sample_rate'] <= 0 or config['language']['code'] != 'ro_RO':
            raise ValueError('Configurație model invalidă.')
        return lock, config
    except (OSError, KeyError, json.JSONDecodeError) as e:
        raise ValueError('Model lipsă/invalid. Rulează ./tts fetch-model.') from e


class Engine:
    def __init__(self, directory=MODEL_DIR):
        from piper import PiperVoice
        import onnxruntime as ort
        ort.disable_telemetry_events()
        started = time.monotonic()
        self.lock, self.config = validate_model(directory)
        self.voice = PiperVoice.load(directory / (VOICE + '.onnx'), use_cuda=False)
        self.sample_rate = self.voice.config.sample_rate
        self.providers = self.voice.session.get_providers()
        if 'CUDAExecutionProvider' in self.providers:
            raise ValueError('Provider GPU neașteptat.')
        self.load_seconds = time.monotonic() - started

    def chunks(self, text, speed):
        from piper import SynthesisConfig
        config = SynthesisConfig(length_scale=self.voice.config.length_scale / speed,
                                 normalize_audio=False)
        for chunk in self.voice.synthesize(text, syn_config=config):
            if chunk.sample_rate != self.sample_rate or chunk.sample_channels != 1:
                raise ValueError('Format Piper neașteptat.')
            yield chunk.audio_float_array


def engine_identity(lock, speed):
    return {'engine': 'piper', 'version': importlib.metadata.version('piper-tts'),
            'adapter': ADAPTER_VERSION, 'voice': VOICE,
            'files': {k: v['sha256'] for k, v in lock['files'].items() if k.endswith(('.onnx', '.json'))},
            'speed': speed, 'normalize_audio': False, 'noise': 'model_defaults', 'provider': 'CPU'}


def fetch_model(directory=MODEL_DIR):
    import urllib.request
    directory.mkdir(parents=True, exist_ok=True)
    # A valid installation is immutable; explicit deletion is required to replace it.
    if (directory / 'model.lock.json').exists():
        validate_model(directory)
        Engine(directory)
        return json.loads((directory / 'model.lock.json').read_text())
    base = 'https://huggingface.co'
    def get_json(url):
        with urllib.request.urlopen(url, timeout=60) as response:
            return json.load(response)
    revision = get_json(base + '/api/models/rhasspy/piper-voices')['sha']
    if len(revision) != 40 or any(c not in '0123456789abcdef' for c in revision):
        raise ValueError('Revizie Hugging Face invalidă.')
    prefix = 'ro/ro_RO/mihai/medium/'
    sources = {VOICE + '.onnx': prefix + VOICE + '.onnx',
               VOICE + '.onnx.json': prefix + VOICE + '.onnx.json',
               'MODEL_CARD': prefix + 'MODEL_CARD', 'VOICE_REPOSITORY_README.md': 'README.md'}
    lock = {'repository': 'rhasspy/piper-voices', 'revision': revision, 'files': {},
            'checksum_note': 'SHA-256 calculat local; nu este o semnătură independentă a furnizorului.'}
    for name, remote in sources.items():
        url = f'{base}/rhasspy/piper-voices/resolve/{revision}/{remote}'
        path = directory / name
        temp = directory / (name + '.part')
        with urllib.request.urlopen(url, timeout=120) as response, temp.open('wb') as f:
            import shutil
            shutil.copyfileobj(response, f, 1024 * 1024)
        if name.endswith('.onnx'):
            if temp.stat().st_size < 1024 * 1024:
                raise ValueError('ONNX prea mic: posibil pointer LFS/HTML.')
            head = temp.open('rb').read(128).lstrip().lower()
            if head.startswith((b'<', b'version https://git-lfs')):
                raise ValueError('Descărcarea nu este model ONNX.')
        elif name.endswith('.json'):
            json.loads(temp.read_text())
        if path.exists() and file_hash(path) != file_hash(temp):
            raise ValueError(f'Fișier existent diferit: {path}; păstrat, verifică manual.')
        os.replace(temp, path)
        lock['files'][name] = {'source': url, 'size': path.stat().st_size, 'sha256': file_hash(path)}
    # Validate ONNX loading BEFORE publishing the lock.
    from piper import PiperVoice
    import onnxruntime as ort
    ort.disable_telemetry_events()
    PiperVoice.load(directory / (VOICE + '.onnx'), use_cuda=False)
    write_json(directory / 'model.lock.json', lock)
    return lock
