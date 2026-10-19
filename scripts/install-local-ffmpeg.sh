#!/bin/bash
# Explicit optional dependency installation, no sudo and no system changes.
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
[ "$(uname -m)" = x86_64 ] || { echo 'Build-ul local fixat este numai x86_64.' >&2; exit 1; }
URL=https://johnvansickle.com/ffmpeg/releases/ffmpeg-7.0.2-amd64-static.tar.xz
HASH=abda8d77ce8309141f83ab8edf0596834087c52467f6badf376a6a2a4c87cf67
ARCHIVE=.tools/downloads/ffmpeg-7.0.2-amd64-static.tar.xz
if [ -e .tools/ffmpeg/ffmpeg ] || [ -e .tools/ffmpeg/ffprobe ]; then
    .tools/ffmpeg/ffmpeg -version
    .tools/ffmpeg/ffprobe -version
    echo 'Instalare existentă păstrată; proveniența este în .tools/ffmpeg.lock.json.'
    exit 0
fi
mkdir -p .tools/downloads .tools/ffmpeg
if [ ! -f "$ARCHIVE" ]; then
    curl -fL --retry 2 "$URL" -o "$ARCHIVE.part"
    printf '%s  %s\n' "$HASH" "$ARCHIVE.part" | sha256sum -c -
    mv -- "$ARCHIVE.part" "$ARCHIVE"
fi
printf '%s  %s\n' "$HASH" "$ARCHIVE" | sha256sum -c -
tar -xJf "$ARCHIVE" --strip-components=1 -C .tools/ffmpeg \
    ffmpeg-7.0.2-amd64-static/ffmpeg ffmpeg-7.0.2-amd64-static/ffprobe \
    ffmpeg-7.0.2-amd64-static/GPLv3.txt ffmpeg-7.0.2-amd64-static/readme.txt
python3 - <<'PY'
import hashlib, json
from pathlib import Path
root = Path('.tools')
files = {n: hashlib.sha256((root / 'ffmpeg' / n).read_bytes()).hexdigest() for n in ['ffmpeg', 'ffprobe']}
(root / 'ffmpeg.lock.json').write_text(json.dumps({
  'url': 'https://johnvansickle.com/ffmpeg/releases/ffmpeg-7.0.2-amd64-static.tar.xz',
  'archive_sha256': 'abda8d77ce8309141f83ab8edf0596834087c52467f6badf376a6a2a4c87cf67',
  'files': files, 'note': 'Hash local al arhivei testate; nu o semnătură independentă a FFmpeg.'
}, indent=2) + '\n')
PY
.tools/ffmpeg/ffmpeg -version
