"""One CPU renderer for full materials, extracts and compilations."""
import hashlib
import math
import os
import re
import shutil
from pathlib import Path
import subprocess
import time
import uuid
from fractions import Fraction
from PIL import Image
from PIL import __version__ as pillow_version

from .core import ROOT, VERSION, assemble, checked, config, ff, key, load, now, probe, read, reference, resolve, sha, tool, write
from .content import fit_image, text_layer
from .subtitles import subtitle_files
from . import asset_render, asset_scenes

# Audited legacy pixel/assembly path stays unchanged; additive branches are versioned.
probe = asset_render.safe_probe

LEGACY_VIDEO_IMPLEMENTATION = "eb6d8044e044583b7fb7c8cb62785f0836cfe135d4d30baff079ccabd327cd58"


def import_scenes(value,path):
    document,m=load(value);data=read(path);scenes=data['scenes'];cursor=0
    if not scenes:raise ValueError('Plan de scene gol.')
    result=[]
    for scene in scenes:
        s=dict(scene)
        if s.get('selected_asset'):
            selected=dict(s['selected_asset']);selected['local_path']=str(resolve(path,selected['local_path']))
            if selected.get('checksum')!=sha(selected['local_path']):raise ValueError('Checksum selected_asset invalid.')
            s.update(asset_schema=1,selected_asset=selected,id=s.get('scene_id',s.get('id')),kind=selected['type'],path=selected['local_path'])
            s.setdefault('anchor',s.get('text',s.get('context','')))
            s.setdefault('visual',{})
            asset_scenes.validate_visual(s['visual'])
            s['approval_status']='pending' if s.get('status','proposed')=='proposed' else s['status']
            for override in s.get('profile_overrides',{}).values():
                if override.get('selected_asset'):
                    a=override['selected_asset'];a['local_path']=str(resolve(path,a['local_path']))
                    if a.get('checksum')!=sha(a['local_path']):raise ValueError('Checksum override invalid.')
                asset_scenes.validate_visual(override.get('visual',{}))
        if s['start']!=cursor or type(s['end']) is not int or s['end']<=cursor or s['end']>m['frames']:raise ValueError('Scene cu gol/suprapunere/interval invalid.')
        asset=resolve(path,s['path'])
        if s['kind'] not in ('image','video'):raise ValueError('Tip vizual invalid.')
        if s.get('motion','none') not in ('none','zoom_in','zoom_out','pan'):raise ValueError('Mișcare necunoscută.')
        if s.get('transition','cut') not in ('cut','crossfade'):raise ValueError('Tranziție necunoscută.')
        focal=s.get('focal',[.5,.5])
        if len(focal)!=2 or any(not isinstance(n,(int,float)) or not math.isfinite(n) or not 0<=n<=1 for n in focal):raise ValueError('Punct focal invalid.')
        if not s.get('anchor'):raise ValueError('Scena necesită pasaj ancoră explicit.')
        if m['text_spoken'] and s['anchor'] not in m['text_spoken']:raise ValueError('Pasajul ancoră nu există în textul rostit.')
        approval=s.get('approval_status','pending')
        if approval not in ('pending','approved','rejected'):raise ValueError('Status de aprobare scenă invalid.')
        s['approval_status']=approval
        s.setdefault('description',s['anchor'])
        if not isinstance(s['description'],str) or not s['description'].strip():raise ValueError('Descriere vizuală goală.')
        text_range=s.get('text_range')
        if text_range is None:
            first=m['text_spoken'].find(s['anchor'])
            if first>=0 and m['text_spoken'].find(s['anchor'],first+1)<0:text_range=[first,first+len(s['anchor'])]
        if text_range is not None:
            a,b=text_range
            if type(a) is not int or type(b) is not int or not 0<=a<b<=len(m['text_spoken']) or m['text_spoken'][a:b]!=s['anchor']:raise ValueError('Interval text scenă invalid.')
        s['text_range']=text_range
        s['asset']=reference(asset,document,license=s.get('license','unknown'),provenance=s.get('provenance','user supplied'))
        s.pop('path');result.append(s);cursor=s['end']
    if cursor!=m['frames']:raise ValueError('Planul nu acoperă întreaga narațiune.')
    m['scenes']=result;write(document.parent/'scenes.json',dict(schema_version=1,scenes=result));write(document,m)
    return result


def verify(path, expected=None):
    p=Path(path);data=probe(p);videos=[s for s in data['streams'] if s['codec_type']=='video'];audios=[s for s in data['streams'] if s['codec_type']=='audio']
    if len(videos)!=1 or len(audios)!=1:raise ValueError('Sunt necesare exact un stream video și unul audio.')
    v,a=videos[0],audios[0]
    if v['codec_name']!='h264' or a['codec_name']!='aac' or v['pix_fmt']!='yuv420p':raise ValueError('Codecuri/formate neconforme.')
    ff(['-xerror','-i',p.resolve(),'-map','0:v:0','-map','0:a:0','-f','null','-'])
    process=subprocess.Popen([tool('ffmpeg'),'-nostdin','-v','error','-xerror','-i',str(p.resolve()),'-map','0:a:0','-ac','1','-f','s32le','pipe:1'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    count=0;h=hashlib.sha256()
    for block in iter(lambda:process.stdout.read(1024*1024),b''):count+=len(block);h.update(block)
    error=process.stderr.read().decode(errors='replace');code=process.wait()
    if code:raise ValueError('Decodare audio eșuată: '+error)
    rate=int(a['sample_rate']);audio_duration=count/4/rate
    fps=Fraction(v['avg_frame_rate']);video_duration=int(v['nb_frames'])/float(fps)
    delta=abs(audio_duration-video_duration)
    if delta>.1:raise ValueError(f'Diferență A/V {delta:.6f}s peste 100 ms.')
    if expected:
        if [v['width'],v['height']]!=expected['size'] or fps!=expected['fps']:raise ValueError('Profil/fps exportat incorect.')
        # Video covers all source samples, then rounds upward to one frame.
        if video_duration+1e-8<expected['frames']/expected['sample_rate'] or video_duration-expected['frames']/expected['sample_rate']>1/float(fps)+1e-6:raise ValueError('Durată video nu acoperă audio-ul planificat.')
        if audio_duration+0.1<expected['frames']/expected['sample_rate']:raise ValueError('Audio decodat mai scurt decât sursa.')
    return dict(technical_status='passed',full_decode=True,format=dict(video_codec=v['codec_name'],audio_codec=a['codec_name'],width=v['width'],height=v['height'],fps=str(fps),audio_sample_rate=rate,channels=a['channels']),
                decoded_audio_seconds=audio_duration,video_seconds=video_duration,av_difference_seconds=delta,
                decoded_audio_sha256=h.hexdigest(),sha256=sha(p),visual_review_status='not_reviewed',listening_status='not_listened')


def scene_key(scene, size, c, title, single):
    # Caption-only options are final composition, not scene pixels. Preserve the
    # pre-style identity exactly for existing receipts, including legacy scenes.
    c={k:v for k,v in c.items() if k!='subtitle_style'}
    if scene.get('asset_schema'):return asset_render.identity(scene,size,c)
    # Version describes the scene pixels/timestamps, independently of final mux.
    return key(dict(pipeline='ffv1-cfr-padding-v2', scene=scene, size=size,
                    config=c, title=title if single else None,
                    pillow=pillow_version, ffmpeg=sha(tool('ffmpeg')),
                    content=sha(Path(__file__).with_name('content.py')), font=sha(c['font'])))


def validate_scene(path, size, fps, frames):
    data=probe(path);streams=data['streams']
    if len(streams)!=1:raise ValueError('Intermediar cu streamuri neașteptate.')
    v=streams[0]
    if v['codec_name']!='ffv1' or v['pix_fmt']!='yuv420p' or [v['width'],v['height']]!=size or Fraction(v['avg_frame_rate'])!=fps:
        raise ValueError('Intermediar incompatibil cu profilul.')
    # Decode and count together: ffprobe packet count alone misses truncation.
    args=[tool('ffmpeg'),'-nostdin','-v','error','-xerror','-threads','2','-i',str(Path(path).resolve()),'-map','0:v:0','-progress','pipe:1','-stats_period','60','-f','null','-']
    count=0
    with Path(path).with_suffix('.decode.stderr').open('w') as log:
        proc=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=log,text=True)
        for line in proc.stdout:
            if line.startswith('frame='):count=int(line.partition('=')[2])
        code=proc.wait()
    if code or count!=frames:raise ValueError(f'Intermediar incomplet: {path}: exit={code}, frames={count}/{frames}')
    return dict(sha256=sha(path),frames=count,codec='ffv1',size=size,fps=fps,full_decode=True)


def logged_ff(args, folder, label):
    attempt=uuid.uuid4().hex
    receipt=folder/f'{label}-{attempt}.command.json'
    command=[tool('ffmpeg'),'-nostdin','-hide_banner','-v','info','-stats_period','5','-threads','2',*[str(a) for a in args]]
    info=dict(created_utc=now(),args=command,cwd=str(folder),phase='running')
    write(receipt,info)
    with receipt.with_suffix('.stderr').open('w') as err, receipt.with_suffix('.stdout').open('w') as out:
        proc=subprocess.Popen(command,cwd=folder,stdout=out,stderr=err)
        info['pid']=proc.pid;write(receipt,info)
        peak_rss_kib=0
        try:
            while proc.poll() is None:
                try:
                    for line in Path(f'/proc/{proc.pid}/status').read_text().splitlines():
                        if line.startswith('VmRSS:'):peak_rss_kib=max(peak_rss_kib,int(line.split()[1]))
                except FileNotFoundError:pass
                time.sleep(.5)
            code=proc.returncode
        except BaseException:
            proc.terminate();proc.wait()
            info.update(phase='interrupted',returncode=proc.returncode,finished_utc=now(),peak_rss_kib=peak_rss_kib)
            write(receipt,info);raise
    info['peak_rss_kib']=peak_rss_kib
    info.update(returncode=code,phase='complete' if code==0 else 'failed',finished_utc=now());write(receipt,info)
    if code:raise ValueError(f'FFmpeg {label}: exit {code}; diagnostic {receipt}')


def render(value, selections,c,image=None,subtitles='off',title=None,force=False,plan_only=False,output_root=None,resume_run=None,rerender_changed=False):
    if rerender_changed and not resume_run:raise ValueError('--rerender-changed cere --resume-run explicit.')
    document,m=load(value);scenes=m['scenes']
    if image:
        scenes=[dict(id='static',start=0,end=m['frames'],kind='image',asset=reference(image,document),anchor=m['text_spoken'],motion='none',transition='cut',focal=[.5,.5],profiles={})]
    if not scenes:raise ValueError('Furnizează imagine sau plan de scene complet.')
    if any(s.get('approval_status')=='rejected' or s.get('review_status')=='REJECTED' for s in scenes):raise ValueError('Scenă rejected; corectează planul înainte de render.')
    cursor=0
    for s in scenes:
        if s['start']!=cursor or s['end']<=s['start']:raise ValueError('Scenele nu acoperă cronologia.')
        checked(document,s['asset']);cursor=s['end']
    if cursor!=m['frames']:raise ValueError('Scene incomplete.')
    for scene in scenes:
        if scene.get('asset_schema'):
            for profile in selections:
                effective=asset_scenes.effective(scene,profile);selected=effective.get('selected_asset')
                if selected and selected.get('provider') not in ('local','graphic','ai-local'):
                    complete=asset_scenes.provenance_complete(selected) and selected.get('downloaded_at') and selected.get('checksum')
                    explicit_unknown=selected.get('unknown_license_explicitly_approved') and selected.get('license') in ('LICENSE_UNKNOWN','unknown') and all(selected.get(k) for k in ('provider','source_url','creator','attribution','downloaded_at','checksum'))
                    if not complete and not explicit_unknown:
                        raise ValueError('Asset online fără provenance/licență aprobată explicit.')
                if effective.get('status')=='rejected':raise ValueError('Scenă rejected.')
                checked(document,effective['asset'])
    if subtitles!='off':
        from .content import valid_words
        valid_words(m)
    plan=dict(material=m['id'],profiles=selections,scene_count=len(scenes),subtitles=subtitles,frames=m['frames'],sample_rate=m['sample_rate'])
    if plan_only:return dict(plan,technical_status='planned')
    started=time.monotonic();run_id=resume_run or uuid.uuid4().hex
    if not re.fullmatch('[0-9a-f]{32}',run_id):raise ValueError('Run-id invalid.')
    work=ROOT/'work/media/runs'/run_id
    if resume_run:
        previous=read(work/'run.json')
        if previous['plan']['material']!=m['id']:raise ValueError('Run pentru alt material.')
        write(work/f'run-before-{uuid.uuid4().hex}.json',previous)
    else:work.mkdir(parents=True)
    state=dict(run_id=run_id,created_utc=now(),phase='running',completed=[],plan=plan)
    write(work/'run.json',state)
    results=[]
    try:
        pcm_receipt=work/'master-receipt.json';pcm=work/(read(pcm_receipt)['path'] if pcm_receipt.exists() else 'master.wav')
        audio_key=key(dict(timeline=m['timeline'],frames=m['frames'],rate=m['sample_rate']))
        for source in m['timeline']:checked(document,source['source'])
        if pcm_receipt.exists() and read(pcm_receipt).get('request')==audio_key and pcm.exists() and read(pcm_receipt)['sha256']==sha(pcm):pass
        else:
            if pcm.exists():pcm=work/f'master-{uuid.uuid4().hex}.wav'
            pcm=assemble(document,m,pcm)
            write(pcm_receipt,dict(request=audio_key,sha256=sha(pcm),path=pcm.name))
        pcm=work/read(pcm_receipt)['path']
        mix_report=None
        if m.get('audio_mix'):
            from . import audio_mix
            pcm,mix_report=audio_mix.render(document,m)
        for name,size in selections.items():
            output=Path(output_root or ROOT/'output/media').resolve()/m['id']/name/'video.mp4';output.parent.mkdir(parents=True,exist_ok=True)
            report_path=output.with_suffix('.report.json')
            profile_scenes=[asset_scenes.effective(scene,name) for scene in scenes]
            extended=any(scene.get('asset_schema') for scene in scenes)
            implementations={n:sha(Path(__file__).parent/n) for n in ('core.py','content.py','video.py')}
            if not extended:implementations['video.py']=LEGACY_VIDEO_IMPLEMENTATION
            else:implementations['asset_render.py']=sha(asset_render.__file__)
            final_config={k:v for k,v in c.items() if k!='subtitle_style'}
            if subtitles!='off':
                from .subtitle_style import effective as caption_style
                style=caption_style(c,size,name);final_config['subtitle_style']=style
                implementations.update({n:sha(Path(__file__).parent/n) for n in ('subtitles.py','subtitle_style.py')})
                implementations['subtitle_font']=sha(style['font'])
            request=key(dict(version=VERSION,pillow=pillow_version,ffmpeg_sha256=sha(tool('ffmpeg')),implementation=implementations,timeline=m['timeline'],scenes=scenes,profile=size,config=final_config,alignment=m['alignment'] if subtitles!='off' else None,subtitles=subtitles,title=title,font=sha(c['font'])))
            picture_request=key(dict(pipeline='composed-picture-v1',size=size,config=final_config,timeline=m['timeline'],scenes=scenes,
                alignment=m['alignment'] if subtitles!='off' else None,subtitles=subtitles,title=title,
                implementation={n:sha(Path(__file__).parent/n) for n in ('content.py','asset_render.py','subtitles.py','subtitle_style.py')},
                font=sha(c['font']),subtitle_font=implementations.get('subtitle_font'),pillow=pillow_version,ffmpeg=sha(tool('ffmpeg'))))
            if mix_report:request=key(dict(picture=request,audio_mix=mix_report['request']))
            if output.exists() and not force:
                if report_path.exists() and read(report_path).get('request')==request and read(report_path).get('sha256')==sha(output):
                    results.append(dict(path=str(output),already_complete=True,verification=verify(output)));continue
                raise ValueError(f'Export existent: {output}; --force explicit necesar.')
            # Audio changes reuse a previously composed picture, including burned
            # subtitles. The normal scene/ASS path is not entered in this branch.
            if mix_report:
                baseline=None
                for export in reversed(m.get('exports',[])):
                    if export.get('profile')!=name or not export.get('report'):continue
                    source=resolve(document,export['path']);rp=resolve(document,export['report']['path'])
                    if source.is_file() and rp.is_file() and sha(source)==export['sha256'] and read(rp).get('picture_request')==picture_request:
                        baseline=source;break
                if baseline:
                    mixed=audio_mix.mux(document,m,baseline,output)
                    verification=mixed['verification']
                    report=dict(request=request,picture_request=picture_request,run_id=run_id,created_utc=now(),profile=name,
                        config=c,sha256=sha(output),verification=verification,audio_mix=mix_report,technical_status='passed',video_packets_identical=True,
                        visual_review_status='not_reviewed',listening_status='not_listened',editorial_review_status='not_reviewed')
                    write(report_path,report);m['exports'].append(reference(output,document,profile=name,request=request,report=reference(report_path,document)))
                    state.setdefault('reused_compositions',[]).append(str(baseline));state['completed'].append(name);write(work/'run.json',state);write(document,m)
                    results.append(dict(path=str(output),verification=verification,video_packets_identical=True));continue
            folder=work/name;folder.mkdir(exist_ok=True)
            fps=c['fps'];rate=m['sample_rate'];clips=[];counts=[];clip_inputs=[];static_input=False;title_baked=False
            for i,scene in enumerate(scenes):
                options=dict(profile_scenes[i])
                if not scene.get('asset_schema'):options.update(options.get('profiles',{}).get(name,{}))
                fit=options.get('fit',c['fit']);focal=options.get('focal',[.5,.5]);motion=options.get('motion','none')
                if fit not in ('contain','cover') or motion not in ('none','zoom_in','zoom_out','pan'):raise ValueError('Încadrare/mișcare invalidă în material.')
                if len(focal)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for v in focal):raise ValueError('Punct focal invalid în material.')
                start=(scene['start']*fps+rate-1)//rate;end=(scene['end']*fps+rate-1)//rate
                n=end-start
                if n<1:raise ValueError('Scenă mai scurtă decât un cadru.')
                extension=round(fps*c['transition_seconds']) if i+1<len(scenes) and profile_scenes[i+1].get('transition','cut')=='crossfade' else 0
                asset=checked(document,options['asset']);clip=folder/f'scene-{i:05d}.mkv';w,h=size
                receipt=clip.with_suffix('.receipt.json')
                if scene.get('asset_schema'):options.update(render_frames=n,render_padding=extension)
                identity=scene_key(options if scene.get('asset_schema') else scene,size,c,title,len(scenes)==1)
                if clip.exists() and receipt.exists() and read(receipt).get('request')!=identity and rerender_changed:
                    old=read(receipt)
                    if old.get('sha256')!=sha(clip):raise ValueError('Intermediar corupt, nu simplu schimbat; păstrat pentru audit.')
                    archive=folder/'revisions'/uuid.uuid4().hex;archive.mkdir(parents=True)
                    os.replace(clip,archive/clip.name);os.replace(receipt,archive/receipt.name)
                    state.setdefault('invalidated_scenes',[]).append(dict(index=i,previous=str(archive/clip.name),request=identity));write(work/'run.json',state)
                if not clip.exists() and rerender_changed:
                    cached_receipts=[*folder.glob('scene-*.receipt.json'),*(folder/'revisions').glob('*/scene-*.receipt.json')]
                    for cached in cached_receipts:
                        saved=read(cached);source=cached.with_name(cached.name.replace('.receipt.json','.mkv'))
                        if saved.get('request')==identity and source.exists() and saved.get('sha256')==sha(source):
                            validate_scene(source,size,fps,n+extension)
                            temporary_copy=folder/('reuse-'+uuid.uuid4().hex+'.part.mkv');shutil.copy2(source,temporary_copy)
                            os.replace(temporary_copy,clip);write(receipt,saved);break
                if clip.exists():
                    if not receipt.exists() or read(receipt).get('request')!=identity or read(receipt).get('sha256')!=sha(clip):
                        raise ValueError(f'Intermediar fără receipt compatibil: {clip}; păstrat pentru audit.')
                    validation=validate_scene(clip,size,fps,n+extension)
                    state.setdefault('reused_scenes',[]).append(str(clip));write(work/'run.json',state)
                    clips.append(clip);counts.append(n);clip_inputs.append(['-threads',str(c['threads']),'-i',clip]);continue
                if scene.get('asset_schema'):
                    temporary_scene=folder/('scene-'+uuid.uuid4().hex+'.part.mkv')
                    ff(asset_render.generate(document,options,size,c,folder,temporary_scene,n,extension))
                    validation=validate_scene(temporary_scene,size,fps,n+extension)
                    os.replace(temporary_scene,clip)
                    write(receipt,dict(request=identity,scene_id=scene.get('scene_id',scene['id']),pipeline=asset_render.PIPELINE,created_utc=now(),**validation))
                    state.setdefault('rendered_scenes',[]).append(str(clip));write(work/'run.json',state)
                    clips.append(clip);counts.append(n);clip_inputs.append(['-threads',str(c['threads']),'-i',clip]);continue
                if scene['kind']=='image':
                    with Image.open(asset) as original:
                        if original.width<w or original.height<h:state.setdefault('warnings',[]).append(f'Imagine sub rezoluția profilului: {asset}')
                        background=fit_image(original,tuple(size),fit,focal)
                    if title and motion=='none' and len(scenes)==1 and c['title_fade_seconds']==0:
                        # An unanimated title is composed once; do not blend a full
                        # transparent HD image over every frame of a long narration.
                        layer,_=text_layer(tuple(size),title,c,'top')
                        background=Image.alpha_composite(background.convert('RGBA'),layer).convert('RGB')
                        title_baked=True
                    bg=folder/f'bg-{i:05d}.png';background.save(bg)
                    args=['-loop','1','-framerate',str(fps),'-i',bg]
                    # A fixed full-length image can feed the final encoder directly.
                    # Avoid writing every identical frame to a large FFV1 intermediate.
                    if motion=='none' and len(scenes)==1:
                        # Decode the PNG once per second, then duplicate decoded YUV
                        # frames BEFORE ASS. Captions still advance at the full fps.
                        args=['-loop','1','-framerate','1','-i',bg]
                        clips.append(bg);counts.append(n);clip_inputs.append(args);static_input=True
                        continue
                    if motion=='none':vf=f'fps={fps}'
                    else:
                        progress=f'on/{max(1,n-1)}'
                        amount=options.get('motion_amount',c['motion_amount'])
                        if type(amount) not in (int,float) or not math.isfinite(amount) or not 0<=amount<=.15:raise ValueError('Intensitate animație invalidă.')
                        zoom={'zoom_in':f'1+{amount}*{progress}','zoom_out':f'1+{amount}-{amount}*{progress}','pan':str(1+amount)}[motion]
                        x=f'(iw-iw/zoom)*{progress}' if motion=='pan' else 'iw/2-iw/zoom/2'
                        vf=f"zoompan=z='{zoom}':x='{x}':y='ih/2-ih/zoom/2':d={n}:s={w}x{h}:fps={fps}"
                else:
                    stream=next(s for s in probe(asset)['streams'] if s['codec_type']=='video')
                    start_seconds=scene.get('source_start',0)
                    available=float(stream.get('duration',probe(asset)['format']['duration']))-start_seconds
                    if available+.1<n/fps:raise ValueError(f'Clip insuficient de lung: {asset}')
                    pad=''
                    if available<n/fps:
                        state.setdefault('warnings',[]).append('Ultimul cadru menținut cel mult 100 ms pentru padding A/V: '+str(asset))
                        pad='tpad=stop_mode=clone:stop_duration=0.1,'
                    args=['-ss',str(start_seconds),'-i',asset]
                    if fit=='contain':vf=pad+f'scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0x14232f,fps={fps}'
                    elif fit=='cover':vf=pad+f'scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}:(iw-ow)*{focal[0]}:(ih-oh)*{focal[1]},fps={fps}'
                    else:raise ValueError('Încadrare necunoscută.')
                # zoompan/trim/setpts can leave frame-rate metadata unset. tpad
                # then emits cloned frames with duplicate timestamps, which the
                # muxer drops. Restore CFR before padding for a full crossfade.
                vf+=f',trim=end_frame={n},setpts=PTS-STARTPTS,fps={fps},tpad=stop_mode=clone:stop={extension},setsar=1,format=yuv420p'
                ff(asset_render.local_inputs([*args,'-vf',vf,'-frames:v',str(n+extension),'-an','-c:v','ffv1','-threads',str(c['threads']),clip]))
                validation=validate_scene(clip,size,fps,n+extension)
                write(receipt,dict(request=identity,created_utc=now(),**validation))
                clips.append(clip);counts.append(n)
                clip_inputs.append(['-threads',str(c['threads']),'-i',clip])
            args=[]
            for inputs in clip_inputs:args+=inputs
            args+=['-threads',str(c['threads']),'-i',pcm];filters=[];label='0:v';cursor=counts[0]
            if static_input:
                filters.append(f'[0:v]format=yuv420p,fps={fps}[still]');label='still'
            for i in range(1,len(clips)):
                if profile_scenes[i].get('transition','cut')=='crossfade':
                    filters.append(f'[{label}][{i}:v]xfade=transition=fade:duration={round(fps*c["transition_seconds"])/fps}:offset={cursor/fps}[v{i}]')
                else:filters.append(f'[{label}][{i}:v]concat=n=2:v=1:a=0[v{i}]')
                label=f'v{i}';cursor+=counts[i]
            if subtitles!='off':
                subdir=folder/'subtitles';subtitle_files(document,m,subdir,size,c,subtitles,name,title)
                # Only project-generated filenames enter filter syntax; user paths are not interpolated.
                filters.append(f'[{label}]ass=filename=subtitles/subtitles.ass:fontsdir=subtitles/fonts[sub]');label='sub'
            if title and not title_baked:
                overlay,layout=text_layer(tuple(size),title,c,'top');overlay.save(folder/'title.png')
                args+=['-threads',str(c['threads']),'-loop','1','-framerate','1','-i',folder/'title.png']
                overlay_index=len(clips)+1
                filters.append(f'[{overlay_index}:v]format=rgba,fps={fps},fade=t=in:d={c["title_fade_seconds"]}:alpha=1[title];[{label}][title]overlay=shortest=1[titled]');label='titled'
            if not filters:filters=[f'[{label}]null[out]'];label='out'
            temporary=output.with_name('.video-'+run_id+'-'+uuid.uuid4().hex+'.part.mp4')
            logged_ff(asset_render.local_inputs([*args,'-filter_complex_threads','1','-filter_complex',';'.join(filters),'-map',f'[{label}]','-map',f'{len(clips)}:a:0',
                '-c:v','libx264','-preset',c['preset'],'-crf',str(c['crf']),'-pix_fmt','yuv420p','-r',str(fps),'-fps_mode','cfr',
                '-c:a','aac','-b:a','128k','-ar',str(rate),'-ac','1','-frames:v',str((m['frames']*fps+rate-1)//rate),
                '-threads',str(c['threads']),'-movflags','+faststart',temporary]),folder,'final')
            verification=verify(temporary,dict(size=size,fps=fps,frames=m['frames'],sample_rate=rate))
            if mix_report:
                audio_check=audio_mix.verify(temporary,rate,folder=folder/'mixed-aac-verify')
                tp=audio_check['loudness']['input_tp']
                if tp is not None and tp>-1:raise ValueError('AAC mix true peak peste pragul existent -1 dBTP; output nepublicat.')
                mix_report=dict(mix_report,mux_verification=audio_check)
            os.replace(temporary,output)
            report=dict(request=request,picture_request=picture_request,audio_mix=mix_report,run_id=run_id,created_utc=now(),material=m['id'],material_sha256=sha(document),profile=name,
                        config=c,sha256=sha(output),verification=verification,technical_status='passed',alignment_status=m['alignment_status'],
                        visual_review_status='not_reviewed',listening_status='not_listened',editorial_review_status='not_reviewed',warnings=state.get('warnings',[]),elapsed_seconds=time.monotonic()-started)
            if extended:asset_scenes.credits(document,output.parent,profiles=[name])
            write(report_path,report);results.append(dict(path=str(output),verification=verification))
            m['exports'].append(reference(output,document,profile=name,request=request,report=reference(report_path,document)))
            state['completed'].append(name);write(work/'run.json',state);write(document,m)
        state['phase']='complete';write(work/'run.json',state)
        return dict(plan,technical_status='passed',run_id=run_id,outputs=results)
    except BaseException as e:
        state['phase']='interrupted' if isinstance(e,KeyboardInterrupt) else 'failed';state['error']=str(e);write(work/'run.json',state);raise
