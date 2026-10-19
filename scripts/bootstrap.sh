#!/bin/bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
export PATH="$PATH:$ROOT/.tools/ffmpeg"
for tool in python3 ffmpeg ffprobe; do
  if ! command -v "$tool" >/dev/null; then
    echo "Lipsește $tool. Rulează: sudo apt-get update && sudo apt-get install -y python3 python3-venv ffmpeg libsndfile1 ca-certificates" >&2
    exit 1
  fi
done
if [ ! -x .venv/bin/python ]; then python3 -m venv .venv; fi
.venv/bin/python -m pip install --require-hashes -r requirements.lock
.venv/bin/python -m pip check
printf '%s\n' 'Instalare completă. Descarcă explicit vocea: ./tts fetch-model'
