import json
import math
from pathlib import Path
import re
import subprocess

import numpy as np
import soundfile as sf

from .cache import CACHE


def command(args):
    try:
        p = subprocess.run(args, capture_output=True, text=True, check=False)
    except FileNotFoundError as e:
        raise ValueError('Lipsește FFmpeg/ffprobe. Rulează bash scripts/bootstrap.sh.') from e
    if p.returncode:
        raise ValueError(f'{args[0]} a eșuat ({p.returncode}): {p.stderr[-4000:]}')
    return p


def assemble(segments, destination, rate, config, cache=CACHE):
    total = 0
    silence = np.zeros(rate, dtype='float32')
    def gap(writer, ms):
        frames = round(rate * ms / 1000)
        remaining = frames
        while remaining:
            count = min(remaining, len(silence))
            writer.write(silence[:count])
            remaining -= count
        return frames
    with sf.SoundFile(destination, 'w', samplerate=rate, channels=1, format='RF64', subtype='FLOAT') as out:
        for i, s in enumerate(segments):
            meta = s['audio']
            with sf.SoundFile(cache / (s['cache_key'] + '.wav')) as source:
                previous = 0
                for j, end in enumerate(meta['boundaries']):
                    remaining = end - previous
                    while remaining:
                        block = source.read(min(65536, remaining), dtype='float32')
                        if not len(block):
                            raise ValueError('WAV cache urwany podczas asamblării.')
                        out.write(block)
                        total += len(block)
                        remaining -= len(block)
                    if j < len(meta['boundaries']) - 1:
                        kind = meta.get('boundary_types', ['sentence'] * len(meta['boundaries']))[j]
                        if kind != 'technical':
                            total += gap(out, config['paragraph_gap_ms'] if kind == 'paragraph' else config['sentence_gap_ms'])
                    previous = end
            if i < len(segments) - 1:
                ms = config['paragraph_gap_ms'] if s['boundary'] == 'paragraph' else (
                    config['sentence_gap_ms'] if s['boundary'] == 'sentence' else 0)
                total += gap(out, ms)
    return total


def loudness(path, config):
    filt = (f"loudnorm=I={config['loudness_lufs']}:TP={config['true_peak_db']}:"
            f"LRA={config['loudness_range']}:dual_mono=false:print_format=json")
    p = command(['ffmpeg', '-nostdin', '-hide_banner', '-v', 'info', '-i', str(path), '-af', filt, '-f', 'null', '-'])
    matches = re.findall(r'\{\s*"input_i".*?\}', p.stderr, re.S)
    if not matches:
        raise ValueError('FFmpeg nu a returnat măsurători loudnorm.')
    data = json.loads(matches[-1])
    result = {}
    for key, value in data.items():
        if key == 'normalization_type':
            result[key] = value
        else:
            number = float(value)
            result[key] = number if math.isfinite(number) else None
    return result


def probe(path):
    data = json.loads(command(['ffprobe', '-v', 'error', '-select_streams', 'a', '-show_streams',
                               '-show_format', '-of', 'json', str(path)]).stdout)
    if len(data['streams']) != 1:
        raise ValueError('Se așteaptă un singur stream audio.')
    s = data['streams'][0]
    return {'codec': s['codec_name'], 'channels': s['channels'], 'sample_rate': int(s['sample_rate']),
            'duration': float(data['format']['duration']), 'bit_rate': int(s.get('bit_rate', 0))}


def verify(path, config, expected_seconds=None, expected_rate=None):
    info = probe(path)
    if info['codec'] != 'mp3' or info['channels'] != 1 or info['duration'] <= 0:
        raise ValueError('MP3 invalid: codec, canale sau durată.')
    if expected_rate and info['sample_rate'] != expected_rate:
        raise ValueError('Rată audio diferită de rata modelului.')
    if expected_seconds and abs(info['duration'] - expected_seconds) > max(0.25, expected_seconds * 0.001):
        raise ValueError('Durata MP3 diferă de numărul planificat de eșantioane.')
    command(['ffmpeg', '-nostdin', '-v', 'error', '-xerror', '-i', str(path), '-f', 'null', '-'])
    measurement = loudness(path, config)
    if measurement['input_tp'] is None or measurement['input_i'] is None:
        raise ValueError('Audio fără nivel măsurabil (tăcere sau prea scurt).')
    long_enough = info['duration'] >= 3
    accepted = measurement['input_tp'] <= -1.0 and (
        not long_enough or abs(measurement['input_i'] - config['loudness_lufs']) <= 1)
    return {'format': info, 'measurements': measurement, 'accepted': accepted,
            'full_decode': True, 'loudness_applicable': long_enough,
            'technical_status': 'passed' if accepted else 'failed', 'listening_status': 'not_listened'}


def export(master, temporary, rate, config):
    measured = loudness(master, config)
    required = ['input_i', 'input_tp', 'input_lra', 'input_thresh', 'target_offset']
    if any(measured.get(k) is None for k in required):
        raise ValueError('Măsurători loudnorm nefinite: audio prea scurt sau fără semnal.')
    filt = (f"loudnorm=I={config['loudness_lufs']}:TP={config['true_peak_db']}:"
            f"LRA={config['loudness_range']}:measured_I={measured['input_i']}:"
            f"measured_TP={measured['input_tp']}:measured_LRA={measured['input_lra']}:"
            f"measured_thresh={measured['input_thresh']}:offset={measured['target_offset']}:"
            'linear=true:dual_mono=false:print_format=json')
    attempts = []
    correction = 0.0
    for attempt in range(3):
        filters = filt + (f',volume={correction}dB' if correction else '')
        p = command(['ffmpeg', '-nostdin', '-hide_banner', '-y', '-i', str(master), '-af', filters,
                     '-ar', str(rate), '-ac', '1', '-c:a', 'libmp3lame', '-b:a', config['mp3_bitrate'],
                     '-f', 'mp3', str(temporary)])
        check = verify(temporary, config, sf.info(master).frames / rate, rate)
        norm = re.findall(r'\{\s*"input_i".*?\}', p.stderr, re.S)
        attempts.append({'correction_db': correction, 'verification': check,
                         'normalization_type': json.loads(norm[-1])['normalization_type'] if norm else 'unknown'})
        if check['accepted']:
            return {'first_pass': measured, 'attempts': attempts, 'verification': check}
        m = check['measurements']
        peak_delta = -1.2 - m['input_tp']
        level_delta = config['loudness_lufs'] - m['input_i']
        correction += min(level_delta, peak_delta)
    raise ValueError(f'Exportul nu respectă pragurile după 3 încercări: {attempts[-1]}')
