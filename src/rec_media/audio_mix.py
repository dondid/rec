"""Offline derived mixes. Narration and alignment are never edited by DSP.

All internal positions are integer samples. Derived segments slice the parent's
processed context, preserving loop phase, envelope state and loudness gain.
"""
from array import array
from copy import deepcopy
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

from . import core

PIPELINE='local-mix-context-v1'


def number(value,low,high,name):
    if type(value) not in (int,float) or not math.isfinite(value) or not low<=value<=high:
        raise ValueError(f'Audio mix: {name} invalid.')
    return value


def samples(value,rate):
    if isinstance(value,bool):raise ValueError('Timestamp audio invalid.')
    try:
        parts=str(value).split(':')
        if len(parts)>3:raise ValueError()
        value=sum(Decimal(p)*60**i for i,p in enumerate(reversed(parts)))
        if not value.is_finite() or value<0:raise ValueError()
        return int((value*rate).to_integral_value(rounding=ROUND_HALF_UP))
    except (InvalidOperation,ValueError):raise ValueError('Timestamp audio invalid; secunde sau HH:MM:SS.fff.')


def source_info(path):
    path=Path(path)
    if not path.is_file():raise ValueError(f'Audio extern inexistent: {path}')
    # No network protocols, including those referenced by a container/playlist.
    data=json.loads(core.run([core.tool('ffprobe'),'-v','error','-protocol_whitelist','file,pipe',
        '-show_streams','-show_format','-of','json',path.resolve()]))
    streams=[s for s in data['streams'] if s['codec_type']=='audio']
    if len(streams)!=1:raise ValueError('Audio extern: exact un stream audio necesar.')
    s=streams[0];duration=float(s.get('duration',data['format'].get('duration',0)))
    if not math.isfinite(duration) or duration<=0 or int(s.get('sample_rate',0))<=0 or not 1<=s.get('channels',0)<=8:
        raise ValueError('Audio extern: durată/rată/canale invalide.')
    return dict(codec=s['codec_name'],sample_rate=int(s['sample_rate']),channels=s['channels'],duration=duration)


def configure(document,m,data,base):
    """Import human config (seconds) as hash-bound, sample-based recipe."""
    if not isinstance(data,dict) or set(data)-{'schema_version','enabled','tracks','ducking','normalization'}:
        raise ValueError('audio_mix config necunoscut.')
    if type(data.get('enabled',False)) is not bool:raise ValueError('enabled cere boolean.')
    if not isinstance(data.get('tracks',[]),list) or len(data.get('tracks',[]))>64:raise ValueError('tracks cere listă de maximum 64 intrări.')
    rate=m['sample_rate'];tracks=[]
    for t in data.get('tracks',[]):
        fields={'type','path','checksum','source','creator','license','start','end','duration','source_start','source_end','volume_db','loop','loop_fade_ms','fade_in','fade_out'}
        if not isinstance(t,dict) or set(t)-fields or t.get('type') not in ('music','sfx','ambience'):
            raise ValueError('Track extern invalid; narration este masterul obligatoriu implicit.')
        if not isinstance(t.get('path'),str) or not t['path'].strip():raise ValueError('Track fără path local.')
        path=core.resolve(base,t['path']);info=source_info(path);digest=core.sha(path)
        if t.get('checksum',digest)!=digest:raise ValueError('Checksum audio extern diferit.')
        decoded_samples=sum(len(a) for a in pcm(path,rate))
        if not decoded_samples:raise ValueError('Audio extern fără eșantioane decodate.')
        info.update(decoded_samples=decoded_samples,decoded_sample_rate=rate)
        start=samples(t.get('start',0),rate)
        if 'duration' in t and 'end' in t:raise ValueError('Alege end sau duration.')
        end=start+samples(t['duration'],rate) if 'duration' in t else samples(t.get('end',m['frames']/rate),rate)
        source_start=samples(t.get('source_start',0),rate);source_end=samples(t['source_end'],rate) if 'source_end' in t else decoded_samples
        if not 0<=start<end<=m['frames'] or not 0<=source_start<source_end<=decoded_samples:
            raise ValueError('Trim/source/timeline în afara limitelor audio.')
        fade_in=samples(t.get('fade_in',0),rate);fade_out=samples(t.get('fade_out',0),rate)
        duration=end-start
        if fade_in>duration or fade_out>duration or fade_in+fade_out>duration:raise ValueError('Fade imposibil pentru durata trackului.')
        loop=t.get('loop',False)
        if type(loop) is not bool or (loop and t['type']=='sfx'):raise ValueError('Loop explicit numai music/ambience.')
        active=duration if loop else min(duration,source_end-source_start)
        if fade_in+fade_out>active:raise ValueError('Fade depășește durata efectivă no-loop.')
        fade_ms=number(t.get('loop_fade_ms',5),0,1000,'loop_fade_ms')
        ref=core.reference(path,document,media=info,source=t.get('source'),creator=t.get('creator'),license=t.get('license','unknown'))
        tracks.append(dict(type=t['type'],source=ref,start=start,end=end,source_start=source_start,source_end=source_end,
            volume_db=number(t.get('volume_db',0),-120,24,'volume_db'),loop=loop,loop_fade_samples=round(fade_ms*rate/1000),fade_in=fade_in,fade_out=fade_out))
    duck=dict(enabled=False,amount_db=12,attack_ms=40,release_ms=350,threshold_db=-40)
    supplied=data.get('ducking',{})
    if not isinstance(supplied,dict) or set(supplied)-set(duck):raise ValueError('Ducking config invalid.')
    duck.update(supplied)
    if type(duck['enabled']) is not bool:raise ValueError('Ducking enabled invalid.')
    for k,lo,hi in [('amount_db',0,60),('attack_ms',1,5000),('release_ms',1,10000),('threshold_db',-100,0)]:number(duck[k],lo,hi,k)
    # Same defaults as rec.json / existing TTS export; not per-track normalization.
    norm=dict(enabled=True,loudness_lufs=-19.0,true_peak_db=-2.0,loudness_range=11.0)
    supplied=data.get('normalization',{})
    if not isinstance(supplied,dict) or set(supplied)-set(norm):raise ValueError('Normalization config invalid.')
    norm.update(supplied)
    if type(norm['enabled']) is not bool:raise ValueError('Normalization enabled invalid.')
    for k,lo,hi in [('loudness_lufs',-36,-5),('true_peak_db',-12,-1),('loudness_range',1,50)]:number(norm[k],lo,hi,k)
    return dict(schema_version=1,timebase='samples',enabled=data.get('enabled',False),tracks=tracks,ducking=duck,normalization=norm)


def absolute(value,document):
    if isinstance(value,list):return [absolute(v,document) for v in value]
    if isinstance(value,dict):
        out={k:absolute(v,document) for k,v in value.items()}
        if 'path' in value and 'sha256' in value:out['path']=str(core.resolve(document,value['path']))
        return out
    return value


def context(document,m):
    return absolute({k:deepcopy(m[k]) for k in ('sample_rate','frames','timeline','audio_mix') if k in m},document)


def derive_context(document,m,start,end,offset=0):
    return dict(start=offset,end=offset+end-start,source_start=start,context=context(document,m),
                parent=dict(material=m['id'],sha256=core.sha(document),interval=[start,end]))


def derived(segments):
    return dict(schema_version=1,timebase='samples',enabled=True,segments=segments)


def fingerprint(document,m,stage='final'):
    c=context(document,m)
    if not c.get('audio_mix',{}).get('enabled'):c['audio_mix']=dict(enabled=False)
    def check(v):
        if isinstance(v,dict):
            if 'path' in v and 'sha256' in v:core.checked(document,v)
            for x in v.values():check(x)
        elif isinstance(v,list):
            for x in v:check(x)
    check(c)
    return core.key(dict(pipeline=PIPELINE,stage=stage,context=c,implementation=core.sha(__file__),
        timeline_implementation=core.sha(Path(__file__).with_name('audio_timeline.py')),assembly_implementation=core.sha(core.__file__),ffmpeg=core.sha(core.tool('ffmpeg'))))


def validate_recipe(document,m):
    spec=m.get('audio_mix',dict(enabled=False))
    if not isinstance(spec,dict) or type(spec.get('enabled')) is not bool:raise ValueError('audio_mix recipe invalid.')
    if not spec['enabled']:return
    if spec.get('schema_version')!=1 or spec.get('timebase')!='samples':raise ValueError('Audio mix schema/timebase invalid.')
    if 'segments' in spec:
        from .audio_timeline import scale
        if 'global_normalization' in spec:configure(document,m,dict(enabled=True,normalization=spec['global_normalization']),document)
        for interval in spec.get('silence_intervals',[]):
            if not isinstance(interval,list) or len(interval)!=2 or any(type(x) is not int for x in interval) or not 0<=interval[0]<interval[1]<=m['frames']:raise ValueError('Interval silence invalid.')
        cursor=0
        for s in spec['segments']:
            if any(type(s.get(k)) is not int for k in ('start','end','source_start')):raise ValueError('Context audio timing invalid.')
            origin=s['context'];a,b=s['start'],s['end'];offset=s['source_start']
            adjustment=s.get('rounding_adjustment',0)
            if type(adjustment) is not int or abs(adjustment)>1:raise ValueError('Ajustare temporală invalidă.')
            if a!=cursor or not a<b<=m['frames'] or not 0<=offset<offset+b-a<=scale(origin['frames'],origin['sample_rate'],m['sample_rate'])+adjustment:raise ValueError('Context audio bounds invalid.')
            validate_recipe(document,origin);cursor=b
        if cursor!=m['frames']:raise ValueError('Context audio coverage invalid.')
        return
    rate=m['sample_rate'];human=dict(enabled=True,ducking=spec['ducking'],normalization=spec['normalization'],tracks=[])
    for t in spec['tracks']:
        if any(type(t.get(k)) is not int for k in ('start','end','source_start','source_end','fade_in','fade_out','loop_fade_samples')):raise ValueError('Track sample timing invalid.')
        ref=t['source'];path=core.checked(document,ref)
        item={k:t[k] for k in ('type','volume_db','loop')}
        item.update(path=str(path),checksum=ref['sha256'],loop_fade_ms=t['loop_fade_samples']*1000/rate)
        for k in ('start','end','source_start','source_end','fade_in','fade_out'):item[k]=str(Decimal(t[k])/rate)
        human['tracks'].append(item)
    verified=configure(document,m,human,document)
    for original,checked in zip(spec['tracks'],verified['tracks']):
        for field in ('codec','sample_rate','channels','duration'):
            if original['source']['media'][field]!=checked['source']['media'][field]:raise ValueError('Metadate audio diferite de fișierul verificat.')


def command(folder,label,args):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);receipt=folder/(label+'-'+uuid.uuid4().hex+'.command.json')
    argv=[core.tool('ffmpeg'),'-nostdin','-hide_banner','-v','info','-xerror','-filter_complex_threads','1','-filter_threads','1',*map(str,args)]
    data=dict(utc=core.now(),phase='running',argv=argv);core.write(receipt,data)
    with receipt.with_suffix('.stdout').open('w') as out,receipt.with_suffix('.stderr').open('w') as err:
        r=subprocess.run(argv,stdout=out,stderr=err)
    data.update(phase='complete' if r.returncode==0 else 'failed',returncode=r.returncode);core.write(receipt,data)
    if r.returncode:raise ValueError(f'Mix FFmpeg exit={r.returncode}; diagnostic: {receipt.with_suffix(".stderr")}')
    return receipt.with_suffix('.stderr').read_text()


def input_args(path):return ['-threads','2','-protocol_whitelist','file,pipe','-i',str(Path(path).resolve())]


def pcm(path,rate):
    proc=subprocess.Popen([core.tool('ffmpeg'),'-nostdin','-v','error','-xerror',*input_args(path),'-map','0:a:0','-ac','1','-ar',str(rate),'-f','f32le','pipe:1'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        while block:=proc.stdout.read(262144):
            a=array('f');a.frombytes(block)
            if sys.byteorder!='little':a.byteswap()
            yield a
        error=proc.stderr.read();code=proc.wait()
        if code:raise ValueError('Full audio decode eșuat: '+error.decode(errors='replace')[-1000:])
    finally:
        if proc.poll() is None:proc.kill();proc.wait()


def measure(path,folder,rate):
    count=0;peak=0.;energy=0.
    for a in pcm(path,rate):
        if any(not math.isfinite(v) for v in a):raise ValueError('PCM non-finite.')
        count+=len(a);peak=max(peak,max(map(abs,a),default=0));energy+=sum(v*v for v in a)
    log=command(folder,'measure',input_args(path)+['-af','loudnorm=I=-19:TP=-2:LRA=11:dual_mono=false:print_format=json','-f','null','-'])
    matches=re.findall(r'\{\s*"input_i".*?\}',log,re.S)
    if not matches:raise ValueError('Lipsesc măsurători loudnorm.')
    raw=json.loads(matches[-1]);values={}
    for k,v in raw.items():
        if k=='normalization_type':continue
        n=float(v);values[k]=n if math.isfinite(n) else None
    return dict(frames=count,peak=peak,peak_db=20*math.log10(peak) if peak else None,rms=math.sqrt(energy/max(1,count)),loudness=values)


def verify(path,rate=None,frames=None,folder=None):
    info=source_info(path);rate=rate or info['sample_rate'];result=measure(path,folder or Path(path).parent/'verify-audio',rate)
    if info['sample_rate']!=rate or info['channels']!=1 or (frames is not None and result['frames']!=frames):raise ValueError('Contract audio/rata/canale/eșantioane diferit.')
    tp=result['loudness']['input_tp']
    if result['peak']>1 or (tp is not None and tp>-.05):raise ValueError('Audio final clipping/true peak invalid.')
    return dict(technical_audio_status='passed',full_decode=True,format=info,**result,listening_review='not_listened')


def envelope(narration,dest,rate,duck):
    """10ms RMS speech-energy detector; bounded gain, one-pole attack/release.

    This is not ASR or CTC review. Attack/release are 63% settling times;
    the detector has at most one 10ms block of lookahead, kept in origin context.
    """
    block=max(1,round(rate*.01));threshold=10**(duck['threshold_db']/20);floor=10**(-duck['amount_db']/20)
    gain=1.;pending=array('f');ranges=[];index=0
    with Path(dest).open('wb') as out:
        def emit(a):
            nonlocal gain,index
            voiced=math.sqrt(sum(v*v for v in a)/len(a))>=threshold
            target=floor if voiced else 1.;time=duck['attack_ms'] if target<gain else duck['release_ms'];alpha=math.exp(-1/(rate*time/1000))
            values=array('f')
            for _ in a:gain=target+(gain-target)*alpha;values.append(gain)
            ranges.append(dict(start=index,end=index+len(a),voiced=voiced,gain_start=values[0],gain_end=values[-1]));index+=len(a)
            if sys.byteorder!='little':values.byteswap()
            values.tofile(out)
        for values in pcm(narration,rate):
            pending.extend(values)
            while len(pending)>=block:emit(pending[:block]);del pending[:block]
        if pending:emit(pending)
    return ranges


def normalization(raw,part,rate,frames,spec,folder):
    first=measure(raw,folder,rate);filters=[];applied='off'
    vals=first['loudness'];required=('input_i','input_tp','input_lra','input_thresh','target_offset')
    pre_gain_db=0
    if spec['enabled'] and ((vals.get('input_i') or -100)>0 or (vals.get('input_tp') or -100)>0):
        # loudnorm measured_I accepts at most 0 LUFS. Keep the unclipped float
        # sum as evidence and attenuate the entire balance before two-pass DSP.
        pre_gain_db=-max(vals.get('input_i') or 0,vals.get('input_tp') or 0)-3
        scaled=Path(folder)/'sum-prescaled-float.wav'
        command(folder,'prescale',input_args(raw)+['-af',f'volume={pre_gain_db}dB','-c:a','pcm_f32le',scaled])
        raw=scaled;vals=measure(raw,folder,rate)['loudness']
    if spec['enabled'] and all(vals.get(k) is not None for k in required):
        filters.append(f"loudnorm=I={spec['loudness_lufs']}:TP={spec['true_peak_db']}:LRA={spec['loudness_range']}:measured_I={vals['input_i']}:measured_TP={vals['input_tp']}:measured_LRA={vals['input_lra']}:measured_thresh={vals['input_thresh']}:offset={vals['target_offset']}:linear=true:dual_mono=false:print_format=json")
        applied='two_pass_final_mix'
    elif first['peak'] and spec['enabled']:
        applied='too_short_for_loudness_peak_only'
    elif not first['peak']:applied='silent_no_loudness_target'
    # Float summation is unclipped. Transparent static attenuation if needed;
    # no per-track loudness normalization and no aggressive hidden hard limiter.
    if not filters and first['loudness']['input_tp'] is not None:
        correction=min(0,spec['true_peak_db']-first['loudness']['input_tp'])
        if correction:filters.append(f'volume={correction}dB');applied+=':static_peak_attenuation'
    filters+= [f'aresample={rate}:resampler=swr:dither_method=none:exact_rational=1',f'apad=whole_len={frames}',f'atrim=end_sample={frames}']
    log=command(folder,'normalize',input_args(raw)+['-af',','.join(filters),'-ac','1','-ar',str(rate),'-c:a','pcm_s32le','-rf64','auto','-f','wav',part])
    result=verify(part,rate,frames,folder)
    tp=result['loudness']['input_tp'];target=spec['true_peak_db']
    retries=[]
    # Dynamic loudnorm may miss its measured target even with supplied first-pass
    # stats. Retry from the ORIGINAL summed float input, never from normalized
    # output or independently normalized parents. Keep every rejected attempt.
    for attempt in range(2):
        measured_i=result['loudness']['input_i']
        if applied!='two_pass_final_mix' or frames/rate<3 or measured_i is None or abs(measured_i-spec['loudness_lufs'])<=1:break
        correction=spec['loudness_lufs']-measured_i
        if tp is not None:correction=min(correction,target-tp)
        previous_offset=float(re.search(r':offset=([^:]+)',filters[0]).group(1))
        offset=previous_offset+correction
        if not -99<=offset<=99:break
        rejected=part.with_name(part.stem+'-rejected-'+uuid.uuid4().hex+part.suffix)
        os.replace(part,rejected)
        retries.append(dict(path=str(rejected),verification=result,offset=previous_offset,correction_db=correction))
        filters[0]=re.sub(r':offset=[^:]+',f':offset={offset:.12g}',filters[0])
        log=command(folder,'normalize-retry-'+str(attempt+1),input_args(raw)+['-af',','.join(filters),'-ac','1','-ar',str(rate),'-c:a','pcm_s32le','-rf64','auto','-f','wav',part])
        result=verify(part,rate,frames,folder);tp=result['loudness']['input_tp']
    if tp is not None and tp>target+.1:raise ValueError('Mix true peak peste ținta configurată; output nepublicat.')
    if applied=='two_pass_final_mix' and frames/rate>=3 and abs(result['loudness']['input_i']-spec['loudness_lufs'])>1:
        raise ValueError('Mix loudness în afara toleranței ±1 LU; output nepublicat.')
    actual=re.findall(r'\{\s*"input_i".*?\}',log,re.S)
    return dict(before=first,after=result,mode=applied,pre_gain_db=pre_gain_db,rejected_attempts=retries,normalization_type=json.loads(actual[-1]).get('normalization_type') if actual else None)


def render(document,m,cache=None,stage='final'):
    if stage not in ('final','pre_normalization'):raise ValueError('Mix stage invalid.')
    validate_recipe(document,m)
    request=fingerprint(document,m,stage);cache=Path(cache or core.ROOT/'work/media/audio-mix');folder=cache/request
    receipt=folder/'receipt.json';final=folder/'mix.wav'
    if receipt.exists():
        saved=core.read(receipt)
        if saved.get('request')==request and final.is_file() and core.sha(final)==saved['sha256']:
            return final,dict(saved,cache_hit=True)
    # Preserve incomplete files/attempts; each retry gets unique intermediates.
    attempt=folder/('attempt-'+uuid.uuid4().hex);attempt.mkdir(parents=True)
    state=dict(utc=core.now(),request=request,phase='running');core.write(attempt/'state.json',state)
    rate=m['sample_rate'];frames=m['frames'];spec=m.get('audio_mix',dict(enabled=False))
    part=attempt/'mix.part.wav'
    try:
        floating=stage=='pre_normalization'
        narration=core.assemble(document,m,attempt/'narration.wav','f32le' if floating else 's32le')
        source_sha=core.sha(narration);normal=None
        if not spec.get('enabled'):
            shutil.copyfile(narration,part)
            verified=dict(technical_audio_status='intermediate',**measure(part,attempt,rate)) if floating else verify(part,rate,frames,attempt)
        elif 'segments' in spec:
            from . import audio_timeline
            intervals=[];cursor=0
            for segment in spec['segments']:
                a,b=segment['start'],segment['end'];origin=segment['context'];offset=segment['source_start']
                adjustment=segment.get('rounding_adjustment',0)
                target_frames=audio_timeline.scale(origin['frames'],origin['sample_rate'],rate)+adjustment
                if type(a) is not int or type(b) is not int or a!=cursor or not a<b<=frames or not 0<=offset<offset+b-a<=target_frames:
                    raise ValueError('Context split/merge audio invalid.')
                origin_stage='pre_normalization' if floating or 'global_normalization' in spec else 'final'
                mixed,_=render(document,origin,cache,origin_stage)
                if origin['sample_rate']!=rate or adjustment:mixed,_=audio_timeline.convert(mixed,rate,origin_stage=='pre_normalization',target_frames=target_frames)
                intervals.append(dict(source=core.reference(mixed,document),start=offset,end=offset+b-a,timeline_start=a));cursor=b
            if cursor!=frames:raise ValueError('Mix derivat cu acoperire incompletă.')
            global_norm=spec.get('global_normalization')
            raw=attempt/'concatenated-float.wav' if floating or global_norm is not None else part
            core.assemble(document,dict(m,timeline=intervals),raw,'f32le' if floating or global_norm is not None else 's32le')
            if floating:shutil.copyfile(raw,part);verified=dict(technical_audio_status='intermediate',**measure(part,attempt,rate))
            elif global_norm is not None:normal=normalization(raw,part,rate,frames,global_norm,attempt);verified=normal['after']
            else:verified=verify(part,rate,frames,attempt)
            positions=[s['start'] for s in spec['segments'] if s['start']]
            if not floating and spec.get('silence_intervals'):
                # Resampling inside loudnorm may ring into explicit silence.
                # Restore only the requested inserted gaps, at sample precision.
                original=attempt/'before-silence-mask.wav';os.replace(part,original)
                masks='+'.join(f'between(n,{a},{b-1})' for a,b in spec['silence_intervals'])
                expression=f'aeval=if(gt({masks},0),0,val(0))'
                command(attempt,'silence-mask',input_args(original)+['-af',expression.replace(',',r'\,'),'-c:a','pcm_s32le','-ar',str(rate),'-ac','1','-rf64','auto',part])
                verified=verify(part,rate,frames,attempt)
                if normal:normal.update(after=verified,explicit_silence_restored=spec['silence_intervals'])
            core.write(attempt/'boundaries.json',audio_timeline.boundaries(part,positions,rate))
        else:
            inputs=input_args(narration);filters=[f'[0:a]aformat=sample_fmts=fltp:channel_layouts=mono[narration]'];labels=['narration']
            duck=spec['ducking'];envelope_index=None
            if duck['enabled']:
                env=attempt/'duck-envelope.f32';ranges=envelope(narration,env,rate,duck);core.write(attempt/'duck-envelope.json',dict(detector='10ms RMS',ranges=ranges))
                envelope_index=1;inputs+=['-threads','2','-f','f32le','-ar',str(rate),'-ac','1','-i',env]
                count=sum(t['type'] in ('music','ambience') for t in spec['tracks'])
                if count:filters.append(f'[1:a]asplit={count}'+''.join(f'[env{j}]' for j in range(count)))
            env_used=0;input_count=2 if envelope_index else 1
            for i,t in enumerate(spec['tracks']):
                path=core.checked(document,t['source']);inputs+=input_args(path);idx=input_count;input_count+=1
                count=t['source_end']-t['source_start'];duration=t['end']-t['start']
                channels=t['source']['media']['channels'];pan='+'.join(f'{1/channels:.17g}*c{j}' for j in range(channels))
                f=f'[{idx}:a]aformat=sample_fmts=fltp,pan=mono|c0={pan},aresample={rate}:resampler=swr:dither_method=none:exact_rational=1,aformat=sample_fmts=fltp:channel_layouts=mono,atrim=start_sample={t["source_start"]}:end_sample={t["source_end"]},asetpts=PTS-STARTPTS'
                if t['loop']:
                    n=min(t['loop_fade_samples'],count//2)
                    if n:f+=f',afade=t=in:ss=0:ns={n},afade=t=out:ss={count-n}:ns={n}'
                    f+=f',aloop=loop=-1:size={count}'
                # Pad silence after a short non-loop source; fades remain anchored
                # to the actual active duration, never to padded silence.
                active=duration if t['loop'] else min(duration,count)
                if t['fade_in']>active or t['fade_out']>active or t['fade_in']+t['fade_out']>active:raise ValueError('Fade depășește durata efectivă no-loop.')
                f+=f',atrim=end_sample={active},volume={t["volume_db"]}dB'
                if t['fade_in']:f+=f',afade=t=in:ss=0:ns={t["fade_in"]}'
                if t['fade_out']:f+=f',afade=t=out:ss={active-t["fade_out"]}:ns={t["fade_out"]}'
                f+=f',adelay={t["start"]}S:all=1,apad=whole_len={frames},atrim=end_sample={frames}[track{i}]';filters.append(f)
                label=f'track{i}'
                if duck['enabled'] and t['type'] in ('music','ambience'):
                    filters.append(f'[{label}][env{env_used}]amultiply[duck{i}]');label=f'duck{i}';env_used+=1
                labels.append(label)
            filters.append(''.join(f'[{label}]' for label in labels)+f'amix=inputs={len(labels)}:normalize=0:duration=first:dropout_transition=0[out]')
            raw=attempt/'sum-float.wav'
            command(attempt,'mix',inputs+['-filter_complex',';'.join(filters),'-map','[out]','-ac','1','-ar',str(rate),'-c:a','pcm_f32le','-rf64','auto',raw])
            if floating:shutil.copyfile(raw,part);verified=dict(technical_audio_status='intermediate',**measure(part,attempt,rate))
            else:normal=normalization(raw,part,rate,frames,spec['normalization'],attempt);verified=normal['after']
        with part.open('rb') as f:os.fsync(f.fileno())
        report=dict(request=request,pipeline=PIPELINE,utc=core.now(),sha256=core.sha(part),narration_sha256=source_sha,
            technical_audio_status='intermediate' if floating else 'passed',stage=stage,cache_hit=False,sample_rate=rate,channels=1,frames=frames,
            configuration=absolute(spec,document),verification=verified,normalization=normal,listening_review='not_listened',attempt=str(attempt))
        if final.exists():
            # A prior unreceipted final is not an approved cache entry.
            os.replace(final,attempt/'previous-unreceipted.wav')
        os.replace(part,final);core.write(receipt,report)
        state.update(phase='complete',receipt=str(receipt));core.write(attempt/'state.json',state)
        return final,report
    except BaseException as e:
        state.update(phase='failed',error=str(e));core.write(attempt/'state.json',state);raise


def mux(document,m,video,output,cache=None):
    """Audio-only final assembly: copy existing compressed video packets."""
    from . import video as renderer
    video=Path(video).resolve();output=Path(output).resolve()
    if output.exists():raise ValueError('MP4 output existent; alege o destinație nouă.')
    baseline=renderer.verify(video)
    if abs(baseline['video_seconds']-m['frames']/m['sample_rate'])>1/float(baseline['format']['fps'])+.001:raise ValueError('Video baseline pentru altă durată material.')
    audio,report=render(document,m,cache);output.parent.mkdir(parents=True,exist_ok=True)
    attempt=output.parent/('mux-'+uuid.uuid4().hex);attempt.mkdir();part=attempt/'mixed.part.mp4'
    command(attempt,'mux',input_args(video)+input_args(audio)+['-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','128k','-ar',str(m['sample_rate']),'-ac','1','-movflags','+faststart',part])
    checked=renderer.verify(part)
    def digest(path):
        text=core.run([core.tool('ffmpeg'),'-nostdin','-v','error',*input_args(path),'-map','0:v:0','-c:v','copy','-f','streamhash','-hash','sha256','-'])
        return text.strip()
    same=digest(video)==digest(part)
    if not same:raise ValueError('Video packets changed during audio mux.')
    audio_check=verify(part,m['sample_rate'],folder=attempt)
    before_loud=report['verification']['loudness'];after_loud=audio_check['loudness']
    if after_loud['input_tp'] is not None and after_loud['input_tp']>-1:raise ValueError('AAC true peak peste pragul existent -1 dBTP.')
    with part.open('rb') as f:os.fsync(f.fileno())
    os.replace(part,output)
    result=dict(utc=core.now(),technical_status='passed',video_packets_identical=True,baseline_sha256=core.sha(video),sha256=core.sha(output),
        audio_mix_request=report['request'],audio_verification=audio_check,pcm_loudness=before_loud,verification=checked,listening_review='not_listened')
    core.write(output.with_suffix('.report.json'),result)
    return result
