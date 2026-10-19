import json
import os
from pathlib import Path
import numpy as np
import soundfile as sf
from .common import ROOT, file_hash, identity, write_json
from .text import segment

CACHE = ROOT / 'work/cache'


def cache_key(spoken, engine):
    value = {'text': spoken, 'engine': engine}
    if len(spoken) > 500:
        value['bounded_expansion_version'] = 1
    return identity(value)


def valid_entry(key, rate, directory=CACHE):
    wav = directory / (key + '.wav')
    try:
        meta = json.loads((directory / (key + '.json')).read_text())
        if meta['key'] != key or meta['sha256'] != file_hash(wav):
            return None
        info = sf.info(wav)
        if (info.samplerate != rate or info.channels != 1 or info.subtype != 'FLOAT'
                or info.frames != meta['frames'] or info.frames <= 0):
            return None
        bounds = meta['boundaries']
        if not bounds or bounds[-1] != info.frames or any(b <= a for a, b in zip([0] + bounds, bounds)):
            return None
        kinds = meta.get('boundary_types', ['sentence'] * len(bounds))
        if len(kinds) != len(bounds) or any(k not in ('sentence', 'technical', 'paragraph', 'end') for k in kinds):
            return None
        with sf.SoundFile(wav) as f:
            for block in f.blocks(blocksize=65536, dtype='float32'):
                if not np.isfinite(block).all():
                    return None
        return meta
    except (OSError, ValueError, KeyError, RuntimeError, TypeError):
        return None


def synthesize(key, engine, spoken, speed, directory=CACHE):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (key + '.wav')
    temp = directory / (key + '.wav.part')
    boundaries, kinds, frames = [], [], 0
    # A pronunciation can expand a short source into many words. Bound inference
    # without imposing a document limit or adding pauses at technical cuts.
    units = segment(spoken, 300, 500) if len(spoken) > 500 else [{'text': spoken, 'boundary': 'end'}]
    with sf.SoundFile(temp, 'w', samplerate=engine.sample_rate, channels=1,
                      format='RF64', subtype='FLOAT') as f:
        for unit in units:
            count = len(boundaries)
            for chunk in engine.chunks(unit['text'], speed):
                chunk = np.asarray(chunk, dtype='float32').reshape(-1)
                if not len(chunk) or not np.isfinite(chunk).all():
                    raise ValueError('Audio Piper gol sau ne-finit.')
                f.write(chunk)
                frames += len(chunk)
                boundaries.append(frames)
                kinds.append('sentence')
            if len(boundaries) == count:
                raise ValueError('Piper nu a generat audio pentru o parte a segmentului.')
            kinds[-1] = unit['boundary']
    if not frames:
        raise ValueError('Piper nu a generat audio pentru segment.')
    meta = {'key': key, 'sha256': file_hash(temp), 'frames': frames,
            'sample_rate': engine.sample_rate, 'boundaries': boundaries, 'boundary_types': kinds}
    os.replace(temp, path)
    write_json(directory / (key + '.json'), meta)
    if not valid_entry(key, engine.sample_rate, directory):
        raise ValueError('Validarea cache-ului a eșuat.')
    return meta
