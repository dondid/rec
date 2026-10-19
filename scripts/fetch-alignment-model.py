#!/usr/bin/env python3
"""Explicit download only; rendering/alignment never accesses the network."""
import hashlib
import json
from pathlib import Path
import urllib.request
import os

ROOT = Path(__file__).resolve().parents[1]
REVISION = '79cf603aac59501d02bfeb37f615efc3ac4ce1b3'
REPOSITORY = 'gigant/romanian-wav2vec2'
FILES = ['config.json', 'vocab.json', 'preprocessor_config.json',
         'tokenizer_config.json', 'special_tokens_map.json', 'added_tokens.json',
         'README.md', 'model.safetensors']


def digest(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    folder = ROOT / 'models/alignment/romanian-wav2vec2'
    folder.mkdir(parents=True, exist_ok=True)
    lock_path = folder / 'model.lock.json'
    old = json.loads(lock_path.read_text()) if lock_path.exists() else {}
    records = {}
    for name in FILES:
        dest = folder / name
        previous = old.get('files', {}).get(name)
        if dest.exists():
            if not previous or digest(dest) != previous['sha256']:
                raise SystemExit(f'Fișier existent nevalidat: {dest}; inspectează-l explicit.')
            records[name] = previous
            continue
        url = f'https://huggingface.co/{REPOSITORY}/resolve/{REVISION}/{name}'
        print(f'Download {name}', flush=True)
        part = dest.with_suffix(dest.suffix + '.part')
        with urllib.request.urlopen(url, timeout=120) as source, part.open('wb') as out:
            while block := source.read(1024 * 1024):
                out.write(block)
        if name.endswith('.json'):
            json.loads(part.read_text())
        if name == 'model.safetensors':
            import struct
            with part.open('rb') as f:
                size = struct.unpack('<Q', f.read(8))[0]
                if not 8 < size < 100_000_000:
                    raise ValueError('Modelul nu este safetensors.')
                json.loads(f.read(size))
        records[name] = dict(source=url, bytes=part.stat().st_size, sha256=digest(part))
        os.replace(part, dest)
        data = dict(repository=REPOSITORY, revision=REVISION, license='Apache-2.0 (model card)',
                    checksum_provenance='locally calculated, not a vendor signature', files=records)
        temp = lock_path.with_suffix('.json.part')
        temp.write_text(json.dumps(data, indent=2) + '\n')
        os.replace(temp, lock_path)
    print(lock_path)


if __name__ == '__main__':
    main()
