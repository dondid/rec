"""CPU forced CTC alignment of known Romanian text; no transcription replacement."""
import argparse
import importlib.metadata
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import unicodedata

from .core import ROOT, assemble, checked, key, load, now, read, reference, resolve, sha, write

ADAPTER = 'ctc-ro-1'
# Inference is unchanged; preserve validated checkpoints across orchestration fixes.
INFERENCE_IDENTITY = 'ed9beca13cc7949f514653a7c491ecfa8fc6cc815d70748dd9a14519124a92da'
MODEL = ROOT / 'models/alignment/romanian-wav2vec2'


def model_identity(folder):
    lock = read(folder / 'model.lock.json')
    required = {'model.safetensors', 'config.json', 'vocab.json', 'preprocessor_config.json'}
    if not required <= lock['files'].keys():
        raise ValueError('Descărcare model incompletă; rulează explicit scripts/fetch-alignment-model.py.')
    for name, item in lock['files'].items():
        p = folder / name
        if p.stat().st_size != item['bytes'] or sha(p) != item['sha256']:
            raise ValueError(f'Model de aliniere corupt: {name}')
    return lock


def windows(document, m):
    """Use actual TTS segment sample counts and application gaps, never text lengths."""
    imported = next((x for x in m['history'] if x['action'] == 'import_tts'), None)
    if not imported:
        if m['frames'] / m['sample_rate'] > 35:
            raise ValueError('Audio lung fără ancore TTS: furnizează --windows cu intervale reale și text cunoscut.')
        return [dict(start=0, end=m['frames'], spoken=m['text_spoken'])]
    manifest = read(checked(document, imported['manifest']))
    report = read(checked(document, next(s for s in m['sources'] if s.get('role') == 'tts_report')))
    c = report['config']; rate = m['sample_rate']; cursor = 0; result = []
    for i, segment in enumerate(manifest['segments']):
        meta = segment['audio']; length = meta['frames']
        for kind in meta.get('boundary_types', ['sentence'] * len(meta['boundaries']))[:-1]:
            if kind != 'technical':
                length += round(rate * c['paragraph_gap_ms' if kind == 'paragraph' else 'sentence_gap_ms'] / 1000)
        result.append(dict(start=cursor, end=cursor + length, spoken=segment['spoken'], segment=i))
        cursor += length
        if i < len(manifest['segments']) - 1:
            kind = segment['boundary']
            cursor += round(rate * (c['paragraph_gap_ms'] if kind == 'paragraph' else c['sentence_gap_ms'] if kind == 'sentence' else 0) / 1000)
    if cursor != report['planned_frames'] or abs(cursor - m['frames']) > round(rate * .1):
        raise ValueError('Ancorele TTS nu corespund eșantioanelor audio decodate.')
    if ' '.join(x['spoken'] for x in result).split() != m['text_spoken'].split():
        raise ValueError('Ancorele TTS nu acoperă textul rostit al materialului.')
    return result


def targets(text, vocab):
    from num2words import num2words
    words = []; pending = []; notes = []
    for token in text.split():
        original = token
        normalized = unicodedata.normalize('NFC', token).lower().translate(str.maketrans('şţŞŢ', 'șțșț'))
        # Only the acoustic target is expanded. Display and original source remain intact.
        def number(match):
            n = match.group()
            if re.fullmatch(r'\d{1,3}(?:\.\d{3})+', n): n = n.replace('.', '')
            if ',' in n:
                left, right = n.split(',')
                return num2words(int(left), lang='ro') + ' virgulă ' + ' '.join(num2words(int(d), lang='ro') for d in right)
            return num2words(int(n), lang='ro')
        normalized = re.sub(r'\d{1,3}(?:\.\d{3})+(?!\d)|\d+(?:,\d+)?', number, normalized)
        normalized = re.sub('[^' + re.escape(''.join(c for c in vocab if len(c) == 1 and c != '|')) + ']+', ' ', normalized).strip()
        normalized = ' '.join(normalized.split())
        if not normalized:
            pending.append(original); continue
        spoken = ' '.join(pending + [original]); pending = []
        words.append(dict(spoken=spoken, display=spoken, alignment_target=normalized))
        if any(c.isdigit() for c in original) or re.search(r'[A-ZĂÂÎȘȚ]{2,}', original):
            notes.append(dict(token=original, target=normalized, reason='Acoustic normalization only; contextual pronunciation not audited.'))
    if pending:
        if not words: raise ValueError('Text fără cuvinte aliniabile.')
        words[-1]['spoken'] += ' ' + ' '.join(pending)
        words[-1]['display'] = words[-1]['spoken']
    ids = []; owners = []
    for i, w in enumerate(words):
        if ids: ids.append(vocab['|']); owners.append(-1)
        for c in w['alignment_target'].replace(' ', '|'):
            ids.append(vocab[c]); owners.append(i)
    if not ids: raise ValueError('Text fără caractere în vocabularul modelului.')
    return words, ids, owners, notes


def viterbi(logp, tokens, blank):
    """Full CTC state graph, including repeated letters, with observed-frame backtracking."""
    import numpy as np
    labels = np.full(2 * len(tokens) + 1, blank, dtype=np.int32)
    labels[1::2] = tokens
    skip = (labels != blank) & (labels != np.roll(labels, 2)); skip[:2] = False
    previous = np.full(len(labels), -np.inf, dtype=np.float32); previous[0] = 0
    back = np.zeros((len(logp), len(labels)), dtype=np.uint8)
    for t, emission in enumerate(logp):
        choices = np.stack([previous, np.r_[-np.inf, previous[:-1]], np.r_[-np.inf, -np.inf, previous[:-2]]])
        choices[2, ~skip] = -np.inf
        best = choices.argmax(axis=0); back[t] = best
        previous = choices[best, np.arange(len(labels))] + emission[labels]
    state = len(labels) - 1 if previous[-1] >= previous[-2] else len(labels) - 2
    if not np.isfinite(previous[state]): raise ValueError('Aliniere imposibilă: prea puține cadre pentru text.')
    frames = [[] for _ in tokens]
    for t in range(len(logp) - 1, -1, -1):
        if state % 2: frames[state // 2].append(t)
        state -= int(back[t, state])
    if any(not f for f in frames): raise ValueError('Caractere nealiniate; nu se inventează timpi.')
    return [list(reversed(f)) for f in frames]


def request_key(m, anchors, model, settings):
    return key(dict(adapter=ADAPTER, timeline=m['timeline'], text=m['text_spoken'], display=m['text_display'],
                    windows=anchors, model=model, settings=settings, implementation=INFERENCE_IDENTITY))


def automatic(value, folder=MODEL, anchors_file=None, max_windows=None, segments=None):
    """Runs in .venv-align; no imports of torch in the media/Piper interpreter."""
    import numpy as np
    import soundfile as sf
    import torch
    from transformers import Wav2Vec2FeatureExtractor, Wav2Vec2ForCTC
    from .core import ff
    document, m = load(value); model = model_identity(folder)
    anchors = read(anchors_file)['windows'] if anchors_file else windows(document, m)
    if max_windows is not None:
        if max_windows < 1: raise ValueError('--max-windows trebuie să fie pozitiv.')
        anchors = anchors[:max_windows]
    selected=set(segments or [])
    if any(type(i) is not int or not 0<=i<len(anchors) for i in selected):raise ValueError('Segment de rerulat inexistent.')
    previous = 0
    for anchor in anchors:
        if not previous <= anchor['start'] < anchor['end'] <= m['frames']:
            raise ValueError('Ferestre invalide/suprapuse.')
        if (anchor['end'] - anchor['start']) / m['sample_rate'] > 40:
            raise ValueError('Fereastră peste 40 s: furnizează ancore mai scurte, fără împărțire temporală inventată.')
        previous = anchor['end']
    partial = ' '.join(a['spoken'] for a in anchors).split() != m['text_spoken'].split()
    for clip in m['timeline']: checked(document, clip['source'])
    versions = {n: importlib.metadata.version(n) for n in ['torch','transformers','numpy','soundfile','num2words']}
    settings = dict(rate=16000, threads=2, confidence_warning=.35, versions=versions)
    signature = request_key(m, anchors, model, settings)
    work = ROOT / 'work/media/alignment' / signature; work.mkdir(parents=True, exist_ok=True)
    cache = work / 'result.json'
    if cache.exists() and not selected:
        try:result = read(cache)
        except (OSError,ValueError):result={}
        if result.get('request') == signature and result.get('result_hash') == key(result['alignment']):
            if not partial and (m.get('alignment') or {}).get('request')!=signature: publish(document, m, result['alignment'], cache)
            return dict(result['report'], cache_hit=True, result=str(cache))
    start = time.monotonic()
    from .recovery import prepare_analysis
    pcm, preparation = prepare_analysis(document,m,work)
    analysis_hash = sha(pcm)
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    load_start = time.monotonic()
    processor = Wav2Vec2FeatureExtractor.from_pretrained(folder, local_files_only=True)
    voice = None
    vocab = read(folder / 'vocab.json'); words = []; warnings = []; hits = 0
    for index, anchor in enumerate(anchors):
        a = round(anchor['start'] * 16000 / m['sample_rate']); b = round(anchor['end'] * 16000 / m['sample_rate'])
        window_key = key(dict(request=signature, index=index, analysis_sha256=analysis_hash))
        checkpoint = work / f'window-{index:04d}.json'
        try:old = read(checkpoint) if checkpoint.exists() else None
        except (OSError,ValueError):old=None
        if index not in selected and old and old.get('key') == window_key and old.get('sha256') == key(old['data']):
            data = old['data']; hits += 1
        else:
            if voice is None:
                voice = Wav2Vec2ForCTC.from_pretrained(folder, local_files_only=True, use_safetensors=True).eval()
                load_seconds = time.monotonic() - load_start
            with sf.SoundFile(pcm) as source:
                source.seek(a); samples = source.read(b-a, dtype='float32')
            inputs = processor(samples, sampling_rate=16000, return_tensors='pt')
            with torch.inference_mode():
                logits = voice(**inputs).logits[0].float()
                logp = torch.log_softmax(logits, dim=-1).numpy()
            items, tokens, owners, notes = targets(anchor['spoken'], vocab)
            paths = viterbi(logp, tokens, voice.config.pad_token_id)
            stride = math.prod(voice.config.conv_stride)
            # Convolution receptive field is 400 samples; centres are offset by 200 at 16 kHz.
            receptive = 1; jump = 1
            for kernel, step in zip(voice.config.conv_kernel, voice.config.conv_stride):
                receptive += (kernel-1)*jump; jump *= step
            for j, item in enumerate(items):
                positions = [k for k,o in enumerate(owners) if o == j]
                observed = [t for k in positions for t in paths[k]]
                scores = [float(logp[t,tokens[k]]) for k in positions for t in paths[k]]
                left = max(0, min(observed)*stride + receptive//2 - stride//2)
                right = min(len(samples), max(observed)*stride + receptive//2 + stride//2)
                item.update(start=anchor['start']+round(left*m['sample_rate']/16000),
                            end=min(anchor['end'],anchor['start']+round(right*m['sample_rate']/16000)),
                            confidence=math.exp(sum(scores)/len(scores)), timing='ctc_observed_frames',window=index)
                if item['start'] >= item['end']: raise ValueError(f'Cuvânt fără interval: fereastra {index}, cuvânt {j}')
            data = dict(words=items, normalization=notes)
            write(checkpoint, dict(key=window_key, data=data, sha256=key(data)))
        words.extend(data['words']); warnings.extend(data['normalization'])
        write(work/'progress.json',dict(created_utc=now(),completed=index+1,expected=len(anchors),cache_hits=hits))
        print(f'Aliniere {index+1}/{len(anchors)}; cache={hits}', file=sys.stderr, flush=True)
    low = [dict(index=i,spoken=w['spoken'],confidence=w['confidence'],start=w['start'],end=w['end']) for i,w in enumerate(words) if w['confidence'] < settings['confidence_warning']]
    alignment = dict(schema_version=1,sample_rate=m['sample_rate'],audio_timeline_hash=key(m['timeline']),words=words,
                     provenance='Known-text Romanian Wav2Vec2 forced CTC; no ASR replacement', status='aligned_not_reviewed',
                     backend=ADAPTER, model=model, settings=settings, request=signature,
                     normalization=warnings, low_confidence=low, unaligned_words=[],partial=partial,created_utc=now())
    report = dict(technical_status='passed',alignment_status='aligned_with_warnings' if low or warnings else 'aligned_not_reviewed',
                  analysis_preparation=preparation,rerun_segments=sorted(selected),partial=partial,windows=len(anchors),window_cache_hits=hits,words=len(words),low_confidence_words=len(low),
                  unaligned_words=0,elapsed_seconds=time.monotonic()-start,model_load_seconds=locals().get('load_seconds',0),
                  cache_hit=False,listening_status='not_listened',manual_anchor_accuracy='not_measured',request=signature)
    write(cache,dict(request=signature,alignment=alignment,result_hash=key(alignment),report=report))
    if not partial: publish(document,m,alignment,cache)
    return dict(report,result=str(cache))


def publish(document,m,alignment,cache):
    from .content import import_alignment
    if m.get('alignment',{} ) and m['alignment'].get('request')==alignment.get('request') and m['alignment'].get('words')==alignment['words']:
        return
    # Keep explicit human reviews on unchanged units when another segment is rerun.
    old_words=(m.get('alignment') or {}).get('words',[])
    for old,new in zip(old_words,alignment['words']):
        if all(old.get(k)==new.get(k) for k in ('spoken','start','end','window')) and old.get('review'):
            new['review']=old['review']
    # Reuse the existing validation contract before attaching backend metadata.
    temp = cache.parent/'words.json'; write(temp,alignment)
    import_alignment(document,temp,alignment['provenance'])
    _,m = load(document)
    m['alignment'].update({k:v for k,v in alignment.items() if k not in ('source',)})
    m['alignment_status']='aligned_with_warnings' if alignment['low_confidence'] or alignment['normalization'] else 'aligned_not_reviewed'
    write(document.parent/'alignment.json',m['alignment']);write(document,m)


def launch(value,folder=None,anchors_file=None,max_windows=None,segments=None):
    python = ROOT / '.venv-align/bin/python'
    if not python.exists(): raise ValueError('Lipsește .venv-align; rulează explicit bash scripts/bootstrap-align.sh.')
    document,_ = load(value)
    args=[str(python),'-m','rec_media.alignment',str(document),'--model',str(folder or MODEL)]
    if anchors_file: args += ['--windows',str(Path(anchors_file).resolve())]
    if max_windows is not None: args += ['--max-windows',str(max_windows)]
    if segments:args += ['--segments',','.join(str(i) for i in segments)]
    env=dict(os.environ,HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',TOKENIZERS_PARALLELISM='false',PYTHONPATH=str(ROOT/'src'))
    result=subprocess.run(args,env=env,capture_output=False)
    if result.returncode: raise ValueError(f'Alinierea a eșuat ({result.returncode}); checkpointurile rămân în work/media/alignment/.')
    receipt=read(document.parent/'alignment-last-run.json')
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('material');p.add_argument('--model',type=Path,default=MODEL);p.add_argument('--windows',type=Path);p.add_argument('--max-windows',type=int);p.add_argument('--segments')
    a=p.parse_args()
    result=automatic(a.material,a.model,a.windows,a.max_windows,[int(i) for i in a.segments.split(',')] if a.segments else None)
    document,_=load(a.material);write(document.parent/'alignment-last-run.json',result)
