"""Shared TTS services. Piper and synthesis behavior remain unchanged."""
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


def validate_config(config):
    if config.get('engine') != 'piper' or config.get('voice') != 'ro_RO-mihai-medium':
        raise ValueError('Motorul și vocea acceptate: piper / ro_RO-mihai-medium.')
    bounds = {'speed': (0.8, 1.2), 'segment_target_chars': (1, 10000),
              'segment_max_chars': (1, 10000), 'sentence_gap_ms': (0, 60000),
              'paragraph_gap_ms': (0, 60000), 'loudness_lufs': (-70, -5),
              'true_peak_db': (-9, -1), 'loudness_range': (1, 50)}
    for key, (low, high) in bounds.items():
        value = config.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f'{key} trebuie să fie între {low} și {high}.')
    for key in ('segment_target_chars', 'segment_max_chars'):
        if type(config[key]) is not int:
            raise ValueError(f'{key} trebuie să fie întreg.')
    if config['segment_target_chars'] > config['segment_max_chars']:
        raise ValueError('segment_target_chars depășește segment_max_chars.')
    if config.get('channels') != 1:
        raise ValueError('Se acceptă numai mono.')
    if config.get('mp3_bitrate') not in ('32k', '40k', '48k', '56k', '64k', '80k', '96k', '112k', '128k', '144k', '160k'):
        raise ValueError('Bitrate MP3 invalid pentru rata nativă de 22050 Hz.')
    return config


def doctor():
    import soundfile as sf
    from .audio import command
    from .engine import Engine
    result = {'python': sys.version, 'architecture': os.uname().machine, 'dependencies': {},
              'libsndfile': sf.__libsndfile_version__,
              'free_bytes': shutil.disk_usage(ROOT).free,
              'writable': {str(p): os.access(p, os.W_OK) for p in [ROOT, ROOT / 'work', ROOT / 'output']}}
    ok = True
    for name in ('piper-tts', 'soundfile', 'numpy', 'onnxruntime'):
        try:
            result['dependencies'][name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result['dependencies'][name] = 'MISSING'
            ok = False
    for binary in ('ffmpeg', 'ffprobe'):
        try:
            result[binary] = command([binary, '-version']).stdout.splitlines()[0]
        except ValueError as e:
            result[binary] = str(e)
            ok = False
    try:
        encoders = command(['ffmpeg', '-hide_banner', '-encoders']).stdout
        help_text = command(['ffmpeg', '-hide_banner', '-h', 'filter=loudnorm']).stdout
        result['libmp3lame'] = 'libmp3lame' in encoders
        result['loudnorm'] = 'dual_mono' in help_text
        ok &= result['libmp3lame'] and result['loudnorm']
    except ValueError:
        ok = False
    try:
        engine = Engine()
        result['model'] = engine.lock
        result['providers'] = engine.providers
        result['load_seconds'] = engine.load_seconds
    except Exception as e:
        result['model_error'] = str(e)
        ok = False
    result['technical_status'] = 'passed' if ok else 'failed'
    return result, 0 if ok else 1


def run(args):
    if args.command == 'fetch-model':
        from .engine import fetch_model
        with project_lock():
            result = fetch_model()
    elif args.command == 'doctor':
        result, status = doctor()
        return result, status
    else:
        config = json.loads(args.config.read_text(encoding='utf-8'))
        if getattr(args, 'speed', None) is not None:
            config['speed'] = args.speed
        validate_config(config)
        if args.command == 'verify':
            from .audio import verify
            result = verify(args.audio, config)
            return result, 0 if result['accepted'] else 1
        rules = rules_from(args.pronunciations)
        if args.command == 'prepare':
            from .pipeline import save_preparation
            data = prepare(args.input, rules, config['segment_target_chars'], config['segment_max_chars'])
            with project_lock():
                save_preparation(data, args.output_dir)
            result = {'segments': len(data['segments']), 'warnings': len(data['warnings']), 'directory': str(args.output_dir)}
        else:
            if args.command == 'preview' and args.words <= 0:
                raise ValueError('--words trebuie să fie un întreg pozitiv.')
            from .pipeline import render
            with project_lock():
                result = render(args.input, args.output, config, rules, args.force, args.keep_wav,
                                args.words if args.command == 'preview' else None)
    return result, 0
