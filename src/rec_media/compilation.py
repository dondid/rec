"""Explicit production timelines on top of the existing mix/derive contracts."""
from copy import deepcopy
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
import math
import os
import uuid
from PIL import Image
from . import core,audio_mix,audio_timeline,derive


def retime(m,rate,phase=Fraction(0)):
    old=m['sample_rate'];result=deepcopy(m)
    def rounded(value):return (2*value.numerator+value.denominator)//(2*value.denominator)
    base=rounded(phase*rate)
    def mapped(n):return rounded((phase+Fraction(n,old))*rate)-base
    for field in ('scenes','text_units'):
        for unit in result[field]:
            for k in ('start','end'):unit[k]=mapped(unit[k])
            if unit['end']<=unit['start']:raise ValueError('Conversia ratei ar elimina o unitate temporală; conversie refuzată.')
    if result.get('alignment'):
        words=result['alignment']['words']
        for w in words:
            w['parent_sample_interval']=[w['start'],w['end']]
            for k in ('start','end'):w[k]=mapped(w[k])
            if w['end']<=w['start']:raise ValueError('Unitate CTC sub un eșantion la rata destinație; refuz fără inventarea timpilor.')
        result['alignment']['sample_rate']=rate
        result['alignment']['timing_transform']=dict(source_rate=old,target_rate=rate,rounding='rational half-up',ctc_recomputed=False)
    result['frames']=mapped(m['frames']);result['sample_rate']=rate
    return result


def convert_material(value,identifier,rate=22050):
    p,m=core.load(value);q=core.new_path(identifier)
    attempt=core.ROOT/'work/media/narration-conversion'/('material-'+uuid.uuid4().hex);attempt.mkdir(parents=True)
    narration=core.assemble(p,m,attempt/'narration.wav');converted,report=audio_timeline.convert(narration,rate)
    child=retime(audio_mix.absolute(m,p),rate);child.update(id=identifier,created_utc=core.now(),exports=[])
    child['parents']=[core.reference(p,q,start=0,end=m['frames'],sample_rate=m['sample_rate'])]
    child['timeline']=[dict(source=core.reference(converted,q),start=0,end=child['frames'],timeline_start=0)]
    if child.get('alignment'):child['alignment']=derive.local_alignment(child['alignment'],child['alignment']['words'],child['timeline'])
    if m.get('audio_mix',{}).get('enabled'):
        segment=audio_mix.derive_context(p,m,0,child['frames']);segment['parent']['interval']=[0,m['frames']]
        child['audio_mix']=audio_mix.derived([segment])
    child['narration_conversion']=report;child['history'].append(dict(action='convert_narration',source_rate=m['sample_rate'],target_rate=rate,utc=core.now(),original_alignment_untouched=True))
    core.write(q,child);return str(q)


def validate_visual(spec,base):
    spec=deepcopy(spec or {'mode':'black'})
    if not isinstance(spec,dict) or set(spec)-{'mode','path','time'} or spec.get('mode') not in ('black','graphic','freeze'):raise ValueError('Visual interval adăugat: black, graphic sau freeze.')
    if spec['mode']!='black':
        if not isinstance(spec.get('path'),str):raise ValueError('Graphic/freeze cere path local explicit.')
        p=core.resolve(base,spec['path'])
        if not p.is_file():raise ValueError('Visual local lipsă.')
        spec['source']=dict(path=str(p.resolve()),sha256=core.sha(p));spec['path']=str(p.resolve())
        if spec['mode']=='freeze':
            audio_mix.samples(spec.get('time',0),1000000)
        else:
            with Image.open(p) as image:image.verify()
    return spec


def create(values,identifier,settings,config_path,plan_only=False):
    """New compilation is opt-in; legacy merge remains exact reconstruction."""
    if not isinstance(settings,dict) or set(settings)-{'sample_rate','pause_before','pause_after','pause_between','intro','outro','visual','normalization'}:raise ValueError('Config compilație invalid.')
    rate=settings.get('sample_rate',22050)
    if type(rate) is not int or not 8000<=rate<=192000:raise ValueError('Rata compilației invalidă.')
    pairs=[core.load(v) for v in values]
    if not pairs:raise ValueError('Compilație goală.')
    q=core.new_path(identifier);visual=validate_visual(settings.get('visual'),config_path)
    events=[];offset=0;elapsed=Fraction(0)
    def gap(kind,value):
        nonlocal offset,elapsed
        if not isinstance(value,dict) or set(value)-{'duration','audio','visual'}:raise ValueError('Intro/outro/pause config invalid.')
        elapsed_after=elapsed+audio_timeline.seconds(value.get('duration',0));ticks=elapsed_after*rate
        end=(2*ticks.numerator+ticks.denominator)//(2*ticks.denominator);duration=end-offset
        if duration<=0:raise ValueError('Interval explicit de durată zero/negativ invalid.')
        event=dict(kind=kind,start=offset,end=offset+duration,visual=validate_visual(value.get('visual',settings.get('visual')),config_path))
        if value.get('audio'):
            # Import using exactly the same track/resampling/gain/provenance rules.
            track=deepcopy(value['audio']);track.setdefault('type','music')
            if any(k in track for k in ('start','end','duration')):raise ValueError('Intro/outro audio ocupă intervalul slotului; folosește source_start/source_end.')
            track.update(start=0,duration=str(Decimal(duration)/rate))
            event['audio']=audio_mix.configure(q,dict(frames=duration,sample_rate=rate),dict(enabled=True,tracks=[track],normalization={'enabled':False}),config_path)
        events.append(event);offset+=duration;elapsed=elapsed_after
    if 'intro' in settings:gap('intro',settings['intro'])
    if 'pause_before' in settings:gap('pause_before',dict(duration=settings['pause_before']))
    for i,(p,m) in enumerate(pairs):
        if i and 'pause_between' in settings:gap('pause_between',dict(duration=settings['pause_between']))
        phase=elapsed;elapsed+=Fraction(m['frames'],m['sample_rate']);ticks=elapsed*rate
        new_offset=(2*ticks.numerator+ticks.denominator)//(2*ticks.denominator);frames=new_offset-offset
        if frames<=0:raise ValueError('Material sub un eșantion la rata compilației.')
        events.append(dict(kind='narration',material=m['id'],start=offset,end=new_offset,source=core.reference(p,q),source_rate=m['sample_rate'],source_frames=m['frames'],phase=[phase.numerator,phase.denominator],rounding_adjustment=frames-audio_timeline.scale(m['frames'],m['sample_rate'],rate)))
        offset=new_offset
    if 'pause_after' in settings:gap('pause_after',dict(duration=settings['pause_after']))
    if 'outro' in settings:gap('outro',settings['outro'])
    normalization=audio_mix.configure(q,dict(sample_rate=rate,frames=offset),dict(enabled=True,normalization=settings.get('normalization',{})),config_path)['normalization']
    plan=dict(schema_version=1,kind='compilation',sample_rate=rate,channels=1,sample_format='s32le',rounding='rational half-up',frames=offset,events=events,
              global_normalization=normalization,visual_default='black: no narration or subtitle context in inserted slots',voice_overlap=False)
    if plan_only:return plan
    attempt=core.ROOT/'work/media/compilation'/uuid.uuid4().hex;attempt.mkdir(parents=True);core.write(attempt/'plan.json',plan)
    state=dict(utc=core.now(),phase='running');core.write(attempt/'state.json',state)
    try:
        result=core.base(identifier,rate,offset);result['composition']=deepcopy(pairs[0][1]['composition']);result['profiles']=deepcopy(pairs[0][1]['profiles'])
        segments=[];words=[];all_aligned=all(m.get('alignment') for _,m in pairs);narration_cache={}
        for ordinal,event in enumerate(events):
            a,b=event['start'],event['end'];duration=b-a
            if event['kind']=='narration':
                p=core.checked(q,event['source']);_,m=core.load(p)
                identity=core.key(audio_mix.context(p,dict(m,audio_mix={'enabled':False})))
                if identity not in narration_cache:narration_cache[identity]=core.assemble(p,m,attempt/f'narration-{ordinal}.wav')
                source=narration_cache[identity];converted,conversion=audio_timeline.convert(source,rate,target_frames=duration)
                child=retime(audio_mix.absolute(m,p),rate,Fraction(*event['phase']))
                result['timeline'].append(dict(source=core.reference(converted,q),start=0,end=duration,timeline_start=a))
                result['parents'].append(core.reference(p,q,start=a,end=b));result['sources']+=child['sources']
                for field in ('text_original','text_display','text_spoken'):result[field]+=('\n\n' if result[field] else '')+child[field]
                for scene in child['scenes']:
                    scene['start']+=a;scene['end']+=a;scene['id']=f'{ordinal}-{scene["id"]}'
                    if scene.get('asset_schema'):scene['scene_id']=scene['id']
                    result['scenes'].append(scene)
                if all_aligned:
                    for word in child['alignment']['words']:
                        word['start']+=a;word['end']+=a
                        if word.get('display_group'):word['display_group']=str(ordinal)+':'+word['display_group']
                        words.append(word)
                segment=audio_mix.derive_context(p,m,0,duration,a);segment['parent']['interval']=[0,m['frames']];segment['rounding_adjustment']=event['rounding_adjustment'];segments.append(segment)
                event['conversion']=conversion
            else:
                silence=audio_timeline.silence(duration,rate,attempt/f'gap-{ordinal}')
                origin=dict(sample_rate=rate,frames=duration,timeline=[dict(source=core.reference(silence,q),start=0,end=duration,timeline_start=0)])
                if event.get('audio'):origin['audio_mix']=audio_mix.absolute(event['audio'],q)
                result['timeline'].append(dict(source=core.reference(silence,q),start=0,end=duration,timeline_start=a))
                segments.append(dict(start=a,end=b,source_start=0,context=origin))
                # Ordinary material scenes remain complete for other consumers.
                graphic=attempt/f'slot-{ordinal}.png';v=event['visual']
                if v['mode']=='graphic':graphic=core.checked(config_path,v['source'])
                elif v['mode']=='freeze':audio_mix.command(attempt,'freeze-slot',audio_mix.input_args(core.checked(config_path,v['source']))+['-ss',str(v.get('time',0)),'-frames:v','1',graphic])
                else:Image.new('RGB',(320,180),'black').save(graphic)
                result['scenes'].append(dict(id=f'slot-{ordinal}',start=a,end=b,asset=core.reference(graphic,q),kind='image',anchor='',motion='none',transition='cut',focal=[.5,.5],profiles={}))
        result['audio_mix']=audio_mix.derived(segments);result['audio_mix']['global_normalization']=normalization
        result['audio_mix']['silence_intervals']=[[e['start'],e['end']] for e in events if e['kind']!='narration' and not e.get('audio')]
        if words:
            result['alignment']=derive.local_alignment(dict(schema_version=1,sample_rate=rate,provenance='known parent units, integer offsets only',status='derived_not_reviewed'),words,result['timeline'])
            result['text_units']=[dict(start=w['start'],end=w['end'],spoken=w['spoken'],display=w.get('display',w['spoken']),timing='derived_parent_samples') for w in words]
            result['alignment_status']='derived_not_reviewed'
        result['compilation']=plan;result['history'].append(dict(action='compilation',utc=core.now(),normalization='one final global pass',plan=str(attempt/'plan.json')))
        # Validate coverage before publishing a normal material manifest.
        if sum(c['end']-c['start'] for c in result['timeline'])!=offset:raise ValueError('Compilație fără acoperire exactă.')
        core.write(attempt/'material.json',result);core.write(q,result)
        state.update(phase='complete',material=str(q));core.write(attempt/'state.json',state);return str(q)
    except BaseException as e:state.update(phase='failed',error=str(e));core.write(attempt/'state.json',state);raise


def video(value,videos,output,base,size=(1080,1920),fps=30):
    """Recompose existing burned video; never invoke scene/subtitle generators."""
    from . import video as renderer
    p,m=core.load(value);output=Path(output).resolve()
    if output.exists():raise ValueError('Video compilație existent; alege alt output.')
    if not m.get('compilation'):raise ValueError('Material fără plan de compilație.')
    folder=core.ROOT/'work/media/compilation-video'/uuid.uuid4().hex;folder.mkdir(parents=True)
    args=[];filters=[];labels=[];counts=[];rate=m['sample_rate'];w,h=size
    for i,event in enumerate(m['compilation']['events']):
        start=(event['start']*fps+rate-1)//rate;end=(event['end']*fps+rate-1)//rate;n=end-start
        if n<1:raise ValueError('Interval video sub un cadru; mărește slotul sau folosește export audio.')
        spec=videos.get(event.get('material')) if event['kind']=='narration' else event['visual']
        spec=dict(path=spec) if isinstance(spec,str) else spec
        if event['kind']=='narration' and spec:
            path=core.resolve(base,spec['path'])
            if 'source_start_sample' in spec:
                tick=spec['source_start_sample'];source_rate=spec['sample_rate']
                if type(tick) is not int or tick<0 or type(source_rate) is not int or source_rate<=0:raise ValueError('Video source sample timebase invalid.')
                source_start=(tick*fps+source_rate-1)//source_rate
            else:
                tick=audio_mix.samples(spec.get('source_start',0),1000000);source_start=(tick*fps+999999)//1000000
            args+=audio_mix.input_args(path)
            filt=f'[{i}:v]fps={fps},trim=start_frame={source_start},setpts=PTS-STARTPTS,scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black,tpad=stop_mode=clone:stop_duration=0.1,trim=end_frame={n},setsar=1,format=yuv420p[v{i}]'
        elif spec and spec.get('mode') in ('graphic','freeze'):
            path=core.checked(base,spec['source'])
            if spec['mode']=='freeze':
                png=folder/f'freeze-{i}.png';audio_mix.command(folder,'freeze',audio_mix.input_args(path)+['-ss',str(spec.get('time',0)),'-frames:v','1',png]);path=png
            args+=['-threads','2','-loop','1','-framerate',str(fps),'-i',str(path)]
            filt=f'[{i}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black,trim=end_frame={n},setpts=PTS-STARTPTS,setsar=1,format=yuv420p[v{i}]'
        else:
            args+=['-threads','2','-f','lavfi','-i',f'color=black:s={w}x{h}:r={fps}:d={n/fps:.12f}']
            filt=f'[{i}:v]trim=end_frame={n},setpts=PTS-STARTPTS,format=yuv420p[v{i}]'
        filters.append(filt);labels.append(f'[v{i}]');counts.append(n)
    filters.append(''.join(labels)+f'concat=n={len(labels)}:v=1:a=0[picture]')
    audio,report=audio_mix.render(p,m);args+=audio_mix.input_args(audio)
    part=folder/'video.part.mp4'
    audio_mix.command(folder,'compose',args+['-filter_complex',';'.join(filters),'-map','[picture]','-map',f'{len(labels)}:a:0','-c:v','libx264','-preset','veryfast','-crf','23','-pix_fmt','yuv420p','-r',str(fps),'-c:a','aac','-b:a','128k','-ar',str(rate),'-ac','1','-frames:v',str(sum(counts)),'-threads','2','-movflags','+faststart',part])
    check=renderer.verify(part,dict(size=list(size),fps=fps,frames=m['frames'],sample_rate=rate));audio_check=audio_mix.verify(part,rate,folder=folder)
    if audio_check['loudness']['input_tp'] is not None and audio_check['loudness']['input_tp']>-1:raise ValueError('AAC true peak peste -1 dBTP.')
    output.parent.mkdir(parents=True,exist_ok=True);os.replace(part,output)
    receipt=dict(utc=core.now(),technical_status='passed',verification=check,audio_verification=audio_check,planned_video_frames=sum(counts),events=m['compilation']['events'],
                 scene_generation=False,subtitle_generation=False,source_subtitles='burned video reused with timeline offsets',listening_review='not_listened',sha256=core.sha(output))
    core.write(output.with_suffix('.report.json'),receipt);return receipt
