import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Optional explicit user-local installation. System tools retain precedence.
if (ROOT / '.tools/ffmpeg').is_dir():
    os.environ['PATH'] = os.environ.get('PATH', '') + os.pathsep + str(ROOT / '.tools/ffmpeg')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def identity(value):
    return digest(json.dumps(value, sort_keys=True, ensure_ascii=False).encode())


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.part')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')
    os.replace(temp, path)


@contextlib.contextmanager
def project_lock(root=ROOT):
    (root / 'work').mkdir(exist_ok=True)
    with (root / 'work/project.lock').open('a') as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Altă comandă folosește proiectul. Reîncearcă după terminare.')
        yield
