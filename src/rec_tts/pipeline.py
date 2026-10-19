import datetime
import importlib.metadata
import logging
import os
from pathlib import Path
import shutil
import sys
import time
import uuid

from . import __version__
from . import audio
from .cache import cache_key, synthesize, valid_entry
from .common import ROOT, file_hash, identity, write_json
from .engine import Engine, engine_identity, validate_model
from .text import prepare

log = logging.getLogger(__name__)


def save_preparation(data, directory):
    directory.mkdir(parents=True, exist_ok=True)
    # Never overwrite a user's review files without inspection.
    for name in ('normalized.txt', 'segments.json', 'warnings.json'):
        if (directory / name).exists():
            raise ValueError(f'Fișier review existent: {directory / name}; alege alt director.')
    (directory / 'normalized.txt').write_text(data['normalized'], encoding='utf-8')
    write_json(directory / 'segments.json', data)
    write_json(directory / 'warnings.json', data['warnings'])


def require_space(path, minimum):
    if shutil.disk_usage(path).free < minimum:
        raise ValueError(f'Spațiu insuficient în {path}: necesar cel puțin {minimum} bytes.')


def render(source, output, config, rules, force=False, keep_wav=False, words=None, after_segment=None):
    started = time.monotonic()
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.suffix.lower() != '.mp3' or source == output:
        raise ValueError('Destinația trebuie să fie un MP3 diferit de sursă.')
    if not output.parent.is_dir():
        raise ValueError('Directorul destinației nu există; creează-l explicit.')
    data = prepare(source, rules, config['segment_target_chars'], config['segment_max_chars'], words)
    lock, model_config = validate_model()
    engine_id = engine_identity(lock, config['speed'])
    request = identity({'source': file_hash(source), 'config': config, 'rules': rules,
                        'engine': engine_id, 'words': words, 'keep_wav': keep_wav})
    report_path = output.with_suffix('.report.json')
    master_output = output.with_suffix('.wav')
    if keep_wav and master_output.exists() and not force:
        raise ValueError(f'WAV existent: {master_output}; folosește --force.')
    if output.exists() and not force:
        import json
        try:
            old = json.loads(report_path.read_text())
            if old['request'] == request and old['output_sha256'] == file_hash(output):
                previous = json.loads(Path(old['manifest']).read_text())
                if (previous['state'] != 'complete' or previous['request'] != request
                        or previous['completed'] != len(previous['segments'])
                        or previous['completed'] != old['segments_expected']):
                    raise ValueError('Manifestul anterior nu confirmă finalizarea cererii.')
                check = audio.verify(output, config, old['planned_duration'], old['sample_rate'])
                if check['accepted']:
                    return dict(old, already_complete=True)
        except (OSError, ValueError, KeyError):
            pass
        raise ValueError(f'Destinație existentă: {output}; folosește --force.')
    if report_path.exists() and not output.exists() and not force:
        raise ValueError(f'Raport existent fără MP3: {report_path}; verifică și folosește --force.')
    run_id = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8]
    directory = ROOT / 'work/runs' / run_id
    directory.mkdir(parents=True)
    require_space(directory, 16 * 1024 * 1024)
    require_space(output.parent, 16 * 1024 * 1024)
    manifest = dict(data, run_id=run_id, state='running', request=request, completed=0)
    (directory / 'normalized.txt').write_text(data['normalized'], encoding='utf-8')
    manifest_path = directory / 'manifest.json'
    write_json(manifest_path, manifest)
    engine = None
    cache_hits = 0
    synthesis_seconds = generated_seconds = 0.0
    current = None
    try:
        for s in manifest['segments']:
            current = s['index']
            key = cache_key(s['spoken'], engine_id)
            s['cache_key'] = key
            meta = valid_entry(key, model_config['audio']['sample_rate'])
            if meta:
                cache_hits += 1
                s['cache_hit'] = True
            else:
                if engine is None:
                    engine = Engine()
                require_space(directory, 16 * 1024 * 1024)
                t = time.monotonic()
                meta = synthesize(key, engine, s['spoken'], config['speed'])
                s['synthesis_seconds'] = time.monotonic() - t
                synthesis_seconds += s['synthesis_seconds']
                generated_seconds += meta['frames'] / engine.sample_rate
                s['cache_hit'] = False
            s['audio'] = meta
            s['state'] = 'complete'
            manifest['completed'] += 1
            manifest['timings'] = {'synthesis_seconds': synthesis_seconds,
                                   'generated_audio_seconds': generated_seconds,
                                   'load_seconds': engine.load_seconds if engine else 0}
            write_json(manifest_path, manifest)
            log.info('Segment %d/%d: %s', current + 1, len(manifest['segments']), 'cache' if s['cache_hit'] else 'sintetizat')
            if after_segment:
                after_segment(manifest['completed'])
        processing = time.monotonic()
        rate = model_config['audio']['sample_rate']
        master = directory / 'master.wav'
        frames = audio.assemble(manifest['segments'], master, rate, config)
        # MP3 temporary is on the same filesystem as its final destination.
        temporary = output.with_name('.' + output.name + '.' + run_id + '.part')
        conversion = audio.export(master, temporary, rate, config)
        result = {'request': request, 'run_id': run_id, 'source': str(source), 'source_sha256': file_hash(source),
                  'config': config, 'model': lock, 'engine': engine_id, 'application_version': __version__,
                  'versions': {'python': sys.version,
                               **{name: importlib.metadata.version(name) for name in ('piper-tts', 'onnxruntime', 'numpy', 'soundfile')},
                               'ffmpeg': audio.command(['ffmpeg', '-version']).stdout.splitlines()[0],
                               'ffprobe': audio.command(['ffprobe', '-version']).stdout.splitlines()[0]},
                  'dictionary_sha256': identity(rules), 'segments_expected': len(manifest['segments']),
                  'segments_completed': manifest['completed'], 'cache_hits': cache_hits,
                  'timings': {'load_seconds': engine.load_seconds if engine else 0,
                              'synthesis_seconds': synthesis_seconds, 'generated_audio_seconds': generated_seconds,
                              'rtf': synthesis_seconds / generated_seconds if generated_seconds else None,
                              'processing_seconds': time.monotonic() - processing,
                              'total_seconds': time.monotonic() - started},
                  'planned_frames': frames, 'planned_duration': frames / rate, 'sample_rate': rate,
                  'audio': conversion, 'warnings': ['Lectura contextuală: vezi manifestul local.'] if data['warnings'] else [],
                  'partial_preview': data['partial_preview'], 'output_sha256': file_hash(temporary),
                  'technical_status': 'passed', 'listening_status': 'not_listened',
                  'manifest': str(manifest_path)}
        if keep_wav:
            wav_temp = master_output.with_name('.' + master_output.name + '.' + run_id + '.part')
            shutil.copyfile(master, wav_temp)
            os.replace(wav_temp, master_output)
        os.replace(temporary, output)
        write_json(report_path, result)
        manifest['state'] = 'complete'
        write_json(manifest_path, manifest)
        # Masters are retained in runs for recovery; no implicit cleanup.
        return result
    except BaseException as e:
        manifest['state'] = 'interrupted' if isinstance(e, KeyboardInterrupt) else 'failed'
        manifest['error'] = {'segment': current, 'message': str(e) or type(e).__name__}
        write_json(manifest_path, manifest)
        if isinstance(e, (KeyboardInterrupt, SystemExit)):
            raise
        raise ValueError(f'{e} [segment {current}, manifest: {manifest_path}]') from e
