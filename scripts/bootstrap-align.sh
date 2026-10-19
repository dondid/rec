#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
if [ ! -x .venv-align/bin/python ]; then
    python3 -m venv .venv-align
fi
# Explicit installation command only; neither ./tts nor ./media render invokes this.
.venv-align/bin/python -m pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements-align.lock
.venv-align/bin/python -m pip check
printf '%s\n' 'Modelul se descarcă separat: python3 scripts/fetch-alignment-model.py'
