import argparse
import importlib.metadata
import json
import logging
import math
import os
from pathlib import Path
import shutil
import sys

from .common import ROOT, project_lock
from .text import prepare, rules_from


from .services import validate_config, doctor


def parser():
    p = argparse.ArgumentParser(description='Text românesc UTF-8 → MP3 local, Piper CPU. Procesarea nu folosește rețeaua.')
    p.add_argument('--config', type=Path, default=ROOT / 'rec.json')
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('fetch-model', help='Descarcă explicit modelul oficial și proveniența.')
    sub.add_parser('doctor', help='Verificări locale, fără rețea.')
    verify = sub.add_parser('verify')
    verify.add_argument('audio', type=Path)
    for name in ('prepare', 'preview', 'render'):
        s = sub.add_parser(name)
        s.add_argument('input', type=Path)
        s.add_argument('--pronunciations', type=Path, default=ROOT / 'pronunciations.json')
        s.add_argument('--verbose', action='store_true')
        if name == 'prepare':
            s.add_argument('--output-dir', type=Path, required=True)
        else:
            s.add_argument('-o', '--output', type=Path, required=True)
            s.add_argument('--speed', type=float)
            s.add_argument('--keep-wav', action='store_true')
            s.add_argument('--force', action='store_true')
            if name == 'preview':
                s.add_argument('--words', type=int, default=180)
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO if getattr(args, 'verbose', False) else logging.WARNING,
                        format='%(levelname)s: %(message)s')
    try:
        from .services import run
        result, status = run(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return status
    except KeyboardInterrupt:
        print('Întrerupt. Cache-ul valid a fost păstrat; repetă comanda pentru reluare.', file=sys.stderr)
        return 130
    except Exception as e:
        logging.debug('Detalii', exc_info=True)
        print(f'Eroare: {e}', file=sys.stderr)
        return 1
