"""Read-only scene snapshots rendered by the production pixel/transition backend."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import math
import os
import shutil
import uuid
from PIL import Image
from .. import core, asset_scenes, asset_render, video
from . import security

PIPELINE = 'studio-preview-1'


def finite(value, low, high, name):
    if type(value) not in (int,float) or not math.isfinite(value) or not low<=value<=high:
        raise ValueError(f'{name}: valoare finită între {low} și {high}.')
    return value


def validate(values):
    if not isinstance(values,dict) or set(values)-{'material','scene','profile','profiles','settings','frame_time','frame_profile','kind'}:
        raise ValueError('Parametri preview necunoscuți.')
    p,m=security.material(values['material']);scene=asset_scenes.find(m,values['scene'])
    if values.get('profile') not in (None,'','landscape','portrait'):raise ValueError('Scope preview invalid.')
    profiles=values.get('profiles',['landscape','portrait'])
    if not isinstance(profiles,list) or not profiles or len(profiles)>2 or len(set(profiles))!=len(profiles) or any(x not in ('landscape','portrait') for x in profiles):raise ValueError('Profile preview invalide.')
    if values.get('frame_profile') not in (None,'landscape','portrait'):raise ValueError('Profil frame invalid.')
    if values.get('kind','scene') not in ('scene','transition'):raise ValueError('Tip preview invalid.')
    settings=values.get('settings',{})
    if not isinstance(settings,dict) or set(settings)-{'visual','video'}:raise ValueError('Preview editează numai visual/video.')
    visual=settings.get('visual',{})
    if not isinstance(visual,dict):raise ValueError('visual cere obiect JSON.')
    asset_scenes.validate_visual(visual)
    if not isinstance(settings.get('video',{}),dict) or set(settings.get('video',{}))-{'source_start','source_end','audio_enabled'}:raise ValueError('Video preview invalid.')
    v=settings.get('video',{})
    if v.get('audio_enabled',False) is not False:raise ValueError('Audio asset video rămâne MUTED.')
    start=finite(v.get('source_start',0),0,7200,'source_start');end=v.get('source_end')
    if end is not None:finite(end,start+.000001,7200,'source_end')
    if values.get('frame_time') is not None:finite(values['frame_time'],0,7200,'frame_time')
    # Apply unsaved controls to an in-memory snapshot, never to material.json.
    snapshot=deepcopy(scene);asset_scenes.upgrade(snapshot,m,p)
    scope=values.get('profile');target=snapshot.setdefault('profile_overrides',{}).setdefault(scope,{}) if scope else snapshot
    for key in ('visual','video'):
        if key in settings:target[key]=dict(target.get(key,{}),**settings[key])
    return p,m,snapshot,profiles


def source_metadata(document,scene,rate):
    path=security.media_file(core.checked(document,scene['asset']))
    result=dict(kind=scene['kind'],checksum=core.sha(path),muted=True)
    if scene['kind']=='image':
        with Image.open(path) as image:result.update(width=image.width,height=image.height,source_duration=None)
        return result
    data=asset_render.safe_probe(path);stream=next(s for s in data['streams'] if s['codec_type']=='video')
    duration=float(stream.get('duration') or data['format']['duration']);fps=float(Fraction(stream.get('avg_frame_rate','30/1')))
    if not math.isfinite(fps) or fps<=0:raise ValueError('FPS sursă invalid.')
    start=scene.get('source_start',0);end=scene.get('source_end')
    if end is None:end=duration
    if not 0<=start<end<=duration+.001:raise ValueError('Trim invalid: 0 ≤ source_start < source_end ≤ durata sursei.')
    needed=(scene['end']-scene['start'])/rate;policy=scene.get('short_policy','error');short=end-start+.001<needed
    result.update(width=stream['width'],height=stream['height'],source_duration=duration,source_fps=fps,source_start=start,source_end=end,
                  trim_duration=end-start,required_scene_duration=needed,short_policy=policy,short_clip=short,
                  render_ready=not short or policy in ('loop','freeze'),warning='Clip prea scurt; alege freeze/loop/alt asset.' if short and policy=='error' else None)
    return result


def preview_size(size):
    scale=min(1,960/max(size))
    return [max(64,2*round(x*scale/2)) for x in size]


def verify_artifact(path,record):
    if not path.is_file() or core.sha(path)!=record['sha256']:raise ValueError('Cache preview lipsă/modificat.')
    if record['type']=='image':
        with Image.open(path) as im:
            im.verify()
        with Image.open(path) as im:
            im.load()
            if list(im.size)!=record['size']:raise ValueError('Dimensiuni preview diferite.')
    else:
        result=video.verify(path)
        if result['format']['width']!=record['size'][0] or result['format']['height']!=record['size'][1]:raise ValueError('Format preview diferit.')
        probe=asset_render.safe_probe(path);s=next(x for x in probe['streams'] if x['codec_type']=='video')
        if int(s['nb_frames'])!=record['frames']:raise ValueError('Cadre preview diferite.')


def render(values):
    p,m,snapshot,profiles=validate(values);c=core.config(overrides=m.get('composition',{}))
    c={k:v for k,v in c.items() if k!='subtitle_style'}
    scenes={name:asset_scenes.effective(snapshot,name) for name in profiles}
    metadata={name:source_metadata(p,s,m['sample_rate']) for name,s in scenes.items()}
    kind=values.get('kind','scene');previous={}
    if kind=='transition':
        index=next(i for i,s in enumerate(m['scenes']) if s['id']==snapshot['id'])
        if index==0:raise ValueError('Prima scenă nu are tranziție de intrare; selectează scena următoare.')
        previous={name:asset_scenes.effective(m['scenes'][index-1],name) for name in profiles}
        for name,s in previous.items():source_metadata(p,s,m['sample_rate'])
    sizes={name:preview_size(c['profiles'][name]) for name in profiles}
    # Content bindings: review/provenance/preview fields do not create scene invalidation.
    request=core.key(dict(pipeline=PIPELINE,kind=kind,frame_time=values.get('frame_time'),frame_profile=values.get('frame_profile'),sizes=sizes,
          scenes={k:asset_render.pixel_scene(v) for k,v in scenes.items()},previous={k:asset_render.pixel_scene(v) for k,v in previous.items()},
          config=c,code=core.sha(__file__),renderer=core.sha(video.__file__),assets=core.sha(asset_render.__file__),content=core.sha(Path(asset_render.__file__).with_name('content.py'))))
    root=core.ROOT/'work/studio/previews'/request;receipt=root/'receipt.json'
    if receipt.exists():
        try:
            cached=core.read(receipt)
            if cached['request']!=request:raise ValueError('Receipt pentru alt preview.')
            for record in cached['artifacts']:verify_artifact(security.path(record['path'],exists=True),record)
            return dict(cached['result'],cache_hit=True)
        except (OSError,ValueError,KeyError):pass  # Preserve invalid cache pair and publish only a fresh attempt.
    attempt=root/('attempt-'+uuid.uuid4().hex);attempt.mkdir(parents=True)
    core.write(attempt/'snapshot.json',dict(material=m['id'],source_manifest_sha256=core.sha(p),scene=snapshot,metadata=metadata,values=values))
    core.write(attempt/'state.json',dict(phase='running',created_utc=core.now(),request=request))
    artifacts=[];outputs=[]
    try:
        for profile,size in sizes.items():
            folder=attempt/profile;folder.mkdir();scene=deepcopy(scenes[profile]);meta=metadata[profile]
            if kind=='scene':
                if scene['kind']=='video':
                    desired=values.get('frame_time',meta['source_start']) if profile==values.get('frame_profile',values.get('profile') or profiles[0]) else meta['source_start']
                    if not meta['source_start']<=desired<=meta['source_end']:raise ValueError('Scrub în afara intervalului trim selectat.')
                    interval=max(1/c['fps'],1/meta['source_fps'])*2
                    sampled=min(desired,max(meta['source_start'],meta['source_end']-interval))
                    scene['source_start']=sampled;scene['source_end']=min(meta['source_end'],sampled+interval)
                    meta.update(requested_frame_time=desired,effective_frame_time=sampled)
                clip=folder/'frame.part.mkv';args=asset_render.generate(p,scene,size,c,folder,clip,1,0)
                core.ff(args);validation=video.validate_scene(clip,size,c['fps'],1)
                temporary=folder/'frame.part.png';target=folder/'frame.png'
                core.ff(['-threads','2','-protocol_whitelist','file,pipe','-i',clip,'-frames:v','1','-threads','2',temporary])
                with Image.open(temporary) as image:image.load();assert list(image.size)==size
                with temporary.open('rb') as f:os.fsync(f.fileno())
                os.replace(temporary,target)
                record=dict(path=str(target),sha256=core.sha(target),size=size,type='image')
                outputs.append(dict(profile=profile,**record,metadata=meta,source_frame_validation=validation))
            else:
                hold=max(1,2*round(c['fps']*c['transition_seconds'])/c['fps']);n=math.ceil(hold*c['fps']);rate=m['sample_rate']
                # Silent short fixture: production transition assembly, no narration/TTS/CTC processing.
                frames=round(2*n/c['fps']*rate);silence=folder/'silence.wav'
                core.ff(['-f','lavfi','-i',f'anullsrc=r={rate}:cl=mono','-af',f'atrim=end_sample={frames}','-c:a','pcm_s32le','-threads','2',silence])
                document=folder/'material.json';temporary_material=core.base('preview-'+request[:20],rate,frames)
                temporary_material['timeline']=[dict(source=core.reference(silence,document),start=0,end=frames,timeline_start=0)]
                pair=[deepcopy(previous[profile]),scene];half=round(n/c['fps']*rate)
                for i,s in enumerate(pair):
                    s.update(status='proposed',approval_status='pending',review_status='NEEDS_REVIEW',id=f'preview-scene-{i}',scene_id=f'preview-scene-{i}',asset_schema=1,start=0 if i==0 else half,end=half if i==0 else frames,profiles={},profile_overrides={})
                    s['asset']=dict(s['asset'],path=str(core.resolve(p,s['asset']['path'])))
                    s['visual']={k:v for k,v in asset_render.pixel_scene(s).items() if k in ('fit','motion','motion_amount','crop','zoom','pan','transition','overlay','title_overlay','subtitle_placement','short_policy')}
                    s['visual']['focal_point']=s.get('focal',[.5,.5]);s['transition']='cut' if i==0 else scene.get('transition','cut');s['visual']['transition']=s['transition']
                    if s.get('selected_asset'):s['selected_asset']['local_path']=s['asset']['path']
                temporary_material['scenes']=pair;core.write(document,temporary_material)
                with core.lock():result=video.render(document,{profile:size},c,subtitles='off',output_root=folder/'output')
                target=Path(result['outputs'][0]['path']);record=dict(path=str(target),sha256=core.sha(target),size=size,type='video',frames=2*n)
                verify_artifact(target,record)
                outputs.append(dict(profile=profile,**record,transition=scene.get('transition','cut'),transition_seconds=round(c['fps']*c['transition_seconds'])/c['fps'],window_seconds=2*n/c['fps'],run_id=result['run_id'],muted=True))
            artifacts.append(record)
        result=dict(technical_status='passed',request=request,kind=kind,cache_hit=False,outputs=outputs,created_utc=core.now(),source_manifest_sha256=core.sha(p),
            note='Renderer real, fereastră preview scurtă; fără subtitrări finale. Cadrele folosesc începutul mișcării ferestrei, nu simulează întreaga animație. Fără aprobare editorială/auditivă.')
        if receipt.exists():shutil.copy2(receipt,attempt/'before-receipt.json')
        core.write(receipt,dict(request=request,artifacts=artifacts,result=result));core.write(attempt/'state.json',dict(phase='complete',completed_utc=core.now(),request=request))
        return result
    except BaseException as e:
        core.write(attempt/'state.json',dict(phase='interrupted' if isinstance(e,KeyboardInterrupt) else 'failed',error=str(e),utc=core.now()));raise
