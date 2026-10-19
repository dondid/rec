"""Exact rational timebase conversion and reusable derived PCM artifacts."""
from array import array
from decimal import Decimal,InvalidOperation
from fractions import Fraction
import math
import os
from pathlib import Path
import sys
import uuid
from . import core,audio_mix


def scale(n,source_rate,target_rate):
    if any(type(v) is not int for v in (n,source_rate,target_rate)) or n<0 or min(source_rate,target_rate)<=0:raise ValueError('Sample timebase invalid.')
    return (2*n*target_rate+source_rate)//(2*source_rate)


def seconds(value):
    if isinstance(value,bool):raise ValueError('Durată invalidă.')
    try:
        parts=str(value).split(':')
        if len(parts)>3:raise ValueError()
        n=sum(Decimal(p)*60**i for i,p in enumerate(reversed(parts)))
        if not n.is_finite() or n<0:raise ValueError()
        return Fraction(n)
    except (InvalidOperation,ValueError):raise ValueError('Durată invalidă.')


def convert(path,rate,floating=False,cache=None,target_frames=None):
    if type(rate) is not int or not 8000<=rate<=192000:raise ValueError('Rata internă trebuie să fie 8000–192000 Hz.')
    path=Path(path).resolve();info=audio_mix.source_info(path)
    request=core.key(dict(source=core.sha(path),rate=rate,floating=floating,target_frames=target_frames,code=core.sha(__file__),ffmpeg=core.sha(core.tool('ffmpeg'))))
    folder=Path(cache or core.ROOT/'work/media/narration-conversion')/request;receipt=folder/'receipt.json';final=folder/'audio.wav'
    if receipt.exists() and final.exists():
        saved=core.read(receipt)
        if saved.get('sha256')==core.sha(final):return final,dict(saved,cache_hit=True)
    attempt=folder/('attempt-'+uuid.uuid4().hex);attempt.mkdir(parents=True);state=dict(utc=core.now(),phase='running',request=request);core.write(attempt/'state.json',state)
    try:
        native=0;peak=0
        for a in audio_mix.pcm(path,info['sample_rate']):
            native+=len(a);peak=max(peak,max(map(abs,a),default=0))
        if not native:raise ValueError('Narațiune fără eșantioane.')
        # The decoder used for the count may use a power-preserving stereo
        # downmix. Only enforce peak here for mono; actual conversion is averaged.
        if not floating and info['channels']==1 and peak>1:raise ValueError('Sursa mono depășește 0 dBFS; conversia PCM integer ar clip-ui.')
        natural=scale(native,info['sample_rate'],rate);expected=natural if target_frames is None else target_frames;channels=info['channels']
        if type(expected) is not int or expected<=0 or abs(expected-natural)>1:raise ValueError('Ajustarea de frontieră trebuie să fie maximum un eșantion.')
        filters=[]
        if channels>1:
            pan='+'.join(f'{1/channels:.17g}*c{i}' for i in range(channels));filters+=['aformat=sample_fmts=fltp',f'pan=mono|c0={pan}']
        filters += [f'aresample={rate}:resampler=swr:dither_method=none:exact_rational=1',f'apad=whole_len={expected}',f'atrim=end_sample={expected}']
        part=attempt/'audio.part.wav';codec='pcm_f32le' if floating else 'pcm_s32le'
        audio_mix.command(attempt,'convert',audio_mix.input_args(path)+['-map','0:a:0','-af',','.join(filters),'-ac','1','-ar',str(rate),'-c:a',codec,'-rf64','auto',part])
        output=audio_mix.source_info(part)
        if int(core.probe(part)['streams'][0]['duration_ts'])!=expected or output['sample_rate']!=rate or output['channels']!=1:raise ValueError('Conversie cu durată/format invalid.')
        for a in audio_mix.pcm(part,rate):
            if any(not math.isfinite(v) for v in a):raise ValueError('Conversie PCM nefin ită.')
        result=dict(utc=core.now(),request=request,sha256=core.sha(part),source=dict(path=str(path),sha256=core.sha(path)),source_format=info,
            source_samples=native,frames=expected,rounding_adjustment=expected-natural,sample_rate=rate,channels=1,codec=codec,rounding='rational half-up',cache_hit=False,full_decode=True,listening_review='not_listened')
        with part.open('rb') as f:os.fsync(f.fileno())
        if final.exists():
            os.replace(final,attempt/'previous-unreceipted.wav')
            if receipt.exists():core.write(attempt/'previous-receipt.json',core.read(receipt))
        os.replace(part,final);core.write(receipt,result);state.update(phase='complete');core.write(attempt/'state.json',state)
        return final,result
    except BaseException as e:state.update(phase='failed',error=str(e));core.write(attempt/'state.json',state);raise


def silence(frames,rate,folder):
    if type(frames) is not int or frames<=0:raise ValueError('Pauza explicită trebuie să aibă cel puțin un eșantion.')
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);part=folder/('silence-'+uuid.uuid4().hex+'.part.wav');final=part.with_name(part.name.replace('.part',''))
    audio_mix.command(folder,'silence',['-f','lavfi','-i',f'anullsrc=r={rate}:cl=mono','-af',f'atrim=end_sample={frames}','-c:a','pcm_s32le',part])
    if int(core.probe(part)['streams'][0]['duration_ts'])!=frames:raise ValueError('Pauza are lungime greșită.')
    os.replace(part,final);return final


def boundaries(path,positions,rate,threshold=.25):
    """Report discontinuities; never apply an unrequested universal fade."""
    wanted={n for p in positions for n in range(max(0,p-4),p+4)};found={};cursor=0
    for values in audio_mix.pcm(path,rate):
        for n in wanted.intersection(range(cursor,cursor+len(values))):found[n]=values[n-cursor]
        cursor+=len(values)
    result=[]
    for p in positions:
        before=found.get(p-1);after=found.get(p)
        if before is None or after is None:continue
        delta=abs(after-before)
        result.append(dict(sample=p,before=before,after=after,step=delta,large_step=delta>threshold,
                           nearby=[found.get(n) for n in range(p-4,p+4)]))
    return dict(threshold=threshold,boundaries=result,status='needs_listening' if any(x['large_step'] for x in result) else 'no_large_step_detected',
                fade_applied=False,listening_review='not_listened')
