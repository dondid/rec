"""Studio-only adapters and validated edits; rendering stays in the shared services."""
from copy import deepcopy
from pathlib import Path
import difflib
import hashlib
import os
import shutil
import uuid
from .. import core, asset_scenes
from . import security, catalog


def prepare_request(request, folder):
    if not isinstance(request,dict):raise ValueError('Cerere JSON invalidă.')
    engine=request.get('engine','media');command=request.get('command',[]);values=deepcopy(request.get('values',{}))
    if engine=='studio':
        if command==['scene-preview']:
            from .previews import validate
            validate(values)
            return dict(engine=engine,command=command,values=values,argv=[])
        if command==['audio-import']:
            from .audio_library import validate
            validate(values)
            return dict(engine=engine,command=command,values=values,argv=[])
        if command==['toolchain-check']:
            if values:raise ValueError('Toolchain probe nu acceptă executabile/comenzi din browser.')
            return dict(engine=engine,command=command,values={},argv=[])
        if command==['verify-material']:
            if set(values)!={'material'}:raise ValueError('Parametri verify invalizi.')
            security.material(values['material'])
            return dict(engine=engine,command=command,values=values,argv=[])
        if command!=['subtitle-preview'] or set(values)-{'material','profile','mode','seconds'}:raise ValueError('Operație Studio invalidă.')
        security.material(values['material'])
        if values.get('profile') not in ('landscape','portrait') or values.get('mode') not in ('classic','highlight','scroll'):raise ValueError('Profil/mod invalid.')
        return dict(engine=engine,command=command,values=values,argv=[])

    inline=request.get('inline',{})
    if not isinstance(inline,dict) or set(inline)-{'set','validate','apply','composition','intervals','manual_ranges','metadata','filters','plan','words','videos','sequence'}:raise ValueError('Document inline nepermis.')
    for name,value in inline.items():
        target=folder/(name+'.json')
        def rooted(v):
            if isinstance(v,list):return [rooted(x) for x in v]
            if isinstance(v,dict):
                out={k:rooted(x) for k,x in v.items()}
                for field in ('path','local_path','font'):
                    if isinstance(v.get(field),str) and v[field]:
                        if field=='font' and Path(v[field]).is_absolute() and Path(v[field]).is_relative_to('/usr/share/fonts'):continue
                        out[field]=str(security.path(v[field]))
                return out
            return v
        value=rooted(value);security.validate_references(value,target);core.write(target,value);values[name]=str(target)
    a,argv,spec=catalog.arguments(engine,command,values)
    for f in spec['fields']:
        v=getattr(a,f['name'],None)
        if v is None:continue
        if f['kind']=='path':
            for item in (v if isinstance(v,list) else [v]):
                p=security.path(item)
                if f['name'] in ('output','output_dir','output_root','report'):
                    if not any(p.is_relative_to(core.ROOT/n) for n in ('output','work')):raise ValueError('Destinațiile Studio trebuie să fie în output/ sau work/.')
                if p.is_file() and p.suffix=='.json':security.validate_references(core.read(p),p)
                if p.is_file() and f['name'] in ('audio','video','mux_video','image','images','replace'):security.media_file(p)
        elif f['name']=='material':
            p,m=security.material(v);security.validate_references(m,p)
            for clip in m['timeline']:security.media_file(core.resolve(p,clip['source']['path']))
            for scene in m['scenes']:
                for profile in ('landscape','portrait'):
                    effective=asset_scenes.effective(scene,profile)
                    security.media_file(core.resolve(p,effective['asset']['path']))
        elif f['name']=='materials':
            for mid in v:
                p,m=security.material(mid);security.validate_references(m,p)
        elif f['name'] in ('id','prefix'):security.identifier(v)
    if engine=='media' and command in (['workflow'],['batch']):
        source=a.plan if command==['workflow'] else a.file
        source=security.path(source,exists=True);document=core.read(source)
        steps=document.get('steps' if command==['workflow'] else 'jobs')
        if not isinstance(steps,list) or not 0<len(steps)<=100:raise ValueError('Workflow/batch cere 1–100 etape explicite.')
        normalized=deepcopy(document)
        for i,step in enumerate(normalized['steps' if command==['workflow'] else 'jobs']):
            tool=step.get('tool','media')
            child=namespace_request(tool,step.get('args'),source.parent)
            if child['command'][0] in ('workflow','batch','synthesize-parts','gui','fetch-model'):raise ValueError('Orchestrare recursivă/instalare refuzată.')
            if child['command'] in (['assets','search'],['assets','download']):raise ValueError('Search/Download sunt acțiuni explicite separate în Assets, nu pași online ascunși.')
            if command==['batch'] and child['command'][0] not in ('render','thumbnail','subtitles','titles'):raise ValueError('Batch: render/thumbnail/subtitles/titles.')
            checked=prepare_request(child,folder/('step-'+str(i)))
            step['args']=checked['argv']
            if command==['workflow'] and tool=='tts' and step['args'][:1]==['--config']:
                if Path(step['args'][1])!=core.ROOT/'rec.json':raise ValueError('Workflow TTS existent folosește configurația implicită; custom config se rulează separat.')
                step['args']=step['args'][2:]
            if command==['workflow']:
                security.identifier(step['id'])
                for field in ('inputs','outputs'):
                    if not isinstance(step.get(field,[]),list):raise ValueError('inputs/outputs cere listă.')
                    step[field]=[str(security.path(source.parent/v)) for v in step.get(field,[])]
        normalized_path=source if normalized==document else folder/('normalized-'+source.name)
        if normalized_path!=source:core.write(normalized_path,normalized)
        values['plan' if command==['workflow'] else 'file']=str(normalized_path)
        a,argv,spec=catalog.arguments(engine,command,values)
    if engine=='media' and command==['synthesize-parts']:
        source=security.path(a.manifest,exists=True);plan=core.read(source)
        for part in plan['parts']:
            security.identifier(part['id']);security.path(source.parent/part['path'],exists=True)
    if engine=='media' and command==['align']:
        p,m=security.material(a.material)
        if m.get('studio_text_pending'):raise ValueError('Texte editat separat; confirmă sursa narativă înainte de aliniere.')
        if m.get('alignment') and not a.segments and not a.words:
            # Existing aligner validates hashes/checkpoints. Do not invoke inference just for opening the page.
            from ..review import bindings
            bindings(p,m)
            if m['alignment'].get('audio_timeline_hash')==core.key(m['timeline']):
                raise ValueError('Aliniere existentă pentru aceeași cronologie; folosește segmente explicite pentru rerun.')
    result=dict(engine=engine,command=command,values=values,argv=argv)
    if request.get('expected') is not None:
        import re
        if engine!='media' or command!=['scenes'] or not isinstance(request['expected'],str) or not re.fullmatch('[0-9a-f]{64}',request['expected']):raise ValueError('Identitate optimistic-lock invalidă.')
        result['expected']=request['expected']
    return result


def run_request(request,on_locked=None):
    if request['engine']=='studio':
        if request['command']==['scene-preview']:
            from .previews import render
            return render(request['values'])
        if request['command']==['audio-import']:
            from .audio_library import import_audio
            return import_audio(request['values'])
        if request['command']==['toolchain-check']:
            from .platform_support import toolchain
            return toolchain()
        if request['command']==['verify-material']:return verify_material(request['values']['material'])
        return subtitle_preview(request['values']['material'],request['values']['profile'],request['values']['mode'],request['values']['seconds'])
    a,_,_=catalog.arguments(request['engine'],request['command'],request['values'])
    if request['engine']=='media':
        from ..services import run
        def guarded():
            if request.get('expected'):
                p,_=security.material(a.material)
                if core.sha(p)!=request['expected']:raise ValueError('Material modificat de alt job/sesiune. Reîncarcă înainte de salvare; controalele nesalvate sunt păstrate.')
            if on_locked:on_locked()
        return run(a,on_locked=guarded)
    from rec_tts.services import run
    result,status=run(a)
    if status and isinstance(result,dict):result['technical_status']='failed'
    return result


def scene_keys(m,c,size,profile,title=None):
    from ..video import scene_key
    scenes=[asset_scenes.effective(s,profile) for s in m['scenes']];rate=m['sample_rate'];fps=c['fps'];result={}
    for i,s in enumerate(scenes):
        n=(s['end']*fps+rate-1)//rate-(s['start']*fps+rate-1)//rate
        pad=round(fps*c['transition_seconds']) if i+1<len(scenes) and scenes[i+1].get('transition','cut')=='crossfade' else 0
        if s.get('asset_schema'):s.update(render_frames=n,render_padding=pad)
        result[s['id']]=scene_key(s,size,c,title,len(scenes)==1)
    return result


def invalidation(mid,scene_id,profile,settings=None,candidate=None):
    p,m=security.material(mid);before=deepcopy(m);scene=asset_scenes.find(m,scene_id);asset_scenes.upgrade(scene,m,p)
    target=scene.setdefault('profile_overrides',{}).setdefault(profile,{}) if profile else scene
    if settings:
        if set(settings)-{'visual','video'}:raise ValueError('Preview invalidare acceptă visual/video.')
        for k,v in settings.items():target[k]=dict(target.get(k,{}),**v)
        asset_scenes.validate_visual(target.get('visual',{}))
    if candidate:
        from ..asset_library import Library
        # Read only; never migrate/write the production library for a preview.
        records=library_records();choice=next((x for x in scene.get('alternatives',[]) if x['candidate_id']==candidate),None)
        aid=choice.get('asset_id') if choice else candidate
        asset=next((x for x in records if x['asset_id']==aid),None)
        if not asset:raise ValueError('Candidat nedescărcat/inexistent.')
        asset_scenes.attach(scene,asset,profile,False,False)
    c=core.config(overrides=m.get('composition',{}));changed={}
    for name,size in c['profiles'].items():
        old=scene_keys(before,c,size,name);new=scene_keys(m,c,size,name)
        changed[name]=[sid for sid in old if old[sid]!=new[sid]]
    return dict(changed=changed,note='Chei scene calculate; paddingul scenei precedente poate fi afectat de crossfade. Exportul final se invalidează separat.')


def library_records():
    import sqlite3,json
    db=core.ROOT/'assets/library/library.sqlite3'
    if not db.exists():return []
    with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as c:
        if not c.execute("SELECT 1 FROM sqlite_master WHERE name='assets'").fetchone():return []
        return [json.loads(row[0]) for row in c.execute('SELECT document FROM assets ORDER BY id')]


def text_state(mid):
    p,m=security.material(mid);draft=p.parent/'studio-text.txt';original=m.get('text_original','')
    text=draft.read_text() if draft.exists() else original
    return dict(text=text,sha256=hashlib.sha256(text.encode()).hexdigest(),words=len(text.split()),estimated_seconds=len(text.split())/150*60,
                diff=''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='material source',tofile='draft')),
                warning='Salvarea creează un draft separat. Audio/aliniere rămân legate de sursa originală; resinteza este explicită.')


def save_text(mid,text,expected):
    if not isinstance(text,str) or len(text.encode())>2_000_000:raise ValueError('Text prea mare/invalid.')
    with core.lock():
        current=text_state(mid)
        if current['sha256']!=expected:raise ValueError('Text schimbat de altă sesiune; reîncarcă.')
        p,m=security.material(mid);folder=p.parent/'studio-text-revisions'/uuid.uuid4().hex
        core.write(folder/'before.json',current);core.write(folder/'after.json',dict(text=text))
        draft=p.parent/'studio-text.txt';tmp=draft.with_name('studio-text-'+uuid.uuid4().hex+'.part')
        with tmp.open('w') as f:f.write(text);f.flush();os.fsync(f.fileno())
        os.replace(tmp,draft)
    return text_state(mid)


def save_subtitles(mid,style,expected=None,undo=False):
    from ..subtitle_style import validate
    with core.lock():
        p,m=security.material(mid)
        if expected and core.sha(p)!=expected:raise ValueError('Material modificat; reîncarcă.')
        folder=p.parent/'studio-subtitle-revisions'
        if undo:
            revisions=sorted(folder.glob('*/before.json'),key=lambda x:x.stat().st_mtime_ns)
            if not revisions:raise ValueError('Nicio revizie de restaurat.')
            style=core.read(revisions[-1]).get('composition',{}).get('subtitle_style',{})
        security.validate_references({'subtitle_style':style},p)
        c=core.config(overrides=m.get('composition',{}));c['subtitle_style']=deepcopy(style);validate(c,p.parent)
        audit=folder/uuid.uuid4().hex;core.write(audit/'before.json',m)
        m.setdefault('composition',{})['subtitle_style']=c['subtitle_style'];core.write(audit/'after.json',m);core.write(p,m)
    return dict(technical_status='passed',subtitle_style=c['subtitle_style'],invalidation='Compoziție finală; zero scene invalidate.')


def duplicate(mid,new_id):
    from ..derive import rebase_refs
    with core.lock():
        p,m=security.material(mid);security.identifier(new_id);dest=core.new_path(new_id)
        copied=rebase_refs(m,p,dest);copied.update(id=new_id,exports=[])
        copied['history'].append(dict(action='studio_duplicate_config',utc=core.now(),source_sha256=core.sha(p)))
        if copied.get('alignment'):copied['alignment']['audio_timeline_hash']=core.key(copied['timeline'])
        core.write(dest,copied)
        if copied.get('alignment'):core.write(dest.parent/'alignment.json',copied['alignment'])
    return dict(material=new_id,note='Configurație duplicată; surse comune imuabile, fără copiere/resinteză audio.')


def subtitle_preview(mid,profile,mode,seconds):
    """Rasterize the renderer's real ASS, not a browser approximation."""
    from ..subtitles import subtitle_files
    from ..asset_render import subtitle_positions
    p,m=security.material(mid);c=core.config(overrides=m.get('composition',{}));size=c['profiles'][profile]
    if not isinstance(seconds,(int,float)) or not 0<=seconds<m['frames']/m['sample_rate']:raise ValueError('Timp preview invalid.')
    folder=core.ROOT/'work/studio/exports'/uuid.uuid4().hex
    result=subtitle_files(p,m,folder,size,c,mode,profile)
    ass=core.resolve(p,result['ass']['path'])
    # subtitle_files already uses profile-specific scene placement/layout.
    image=folder/'subtitle-preview.png';w,h=size
    core.ff(['-f','lavfi','-i',f'color=c=0x14232f:s={w}x{h}:r={c["fps"]}:d={seconds+1}',
             '-vf',f"ass=filename='{ass}':fontsdir='{folder}'",'-ss',str(seconds),'-frames:v','1','-threads','2',image])
    return dict(technical_status='passed',path=str(image),layout=result['layout'],mode=mode,profile=profile,
                note='ASS/layout reale pe fundal neutru; nu constituie review vizual/auditiv integral.')


def render_plan(values):
    a,_,_=catalog.arguments('media',['render'],values)
    p,m=security.material(a.material);c=core.config(overrides=m.get('composition',{}));sizes=core.profiles(a.profiles,c,a.width,a.height)
    if a.output_root:security.path(a.output_root)
    from ..video import render
    plan=render(a.material,sizes,c,a.image,a.subtitles,a.title,False,True)
    if a.subtitles!='off':
        from ..subtitles import subtitle_files
        preflight=core.ROOT/'work/studio/preflight'/uuid.uuid4().hex
        for profile,size in sizes.items():subtitle_files(p,m,preflight/profile,size,c,a.subtitles,profile,a.title)
    candidates={}
    runs=core.ROOT/'work/media/runs'
    if a.resume_run:
        if not isinstance(a.resume_run,str) or len(a.resume_run)!=32 or any(x not in '0123456789abcdef' for x in a.resume_run):raise ValueError('Run ID invalid.')
        folders=[runs/a.resume_run]
    else:folders=[]
    for profile,size in sizes.items():
        wanted=scene_keys(m,c,size,profile,a.title);matched=[]
        for i,s in enumerate(m['scenes']):
            for folder in folders:
                receipt=folder/profile/f'scene-{i:05d}.receipt.json'
                try:
                    r=core.read(receipt)
                    if r.get('request')==wanted[s['id']]:matched.append(s['id']);break
                except (OSError,ValueError):continue
        candidates[profile]=dict(total=len(wanted),potential_reused=len(matched),requires_render=len(wanted)-len(matched),matched_scene_ids=matched)
    return dict(plan=plan,profiles=candidates,audio_mix_enabled=m.get('audio_mix',{}).get('enabled',False),
                note='Potențial de reutilizare calculat prin scene_key în run-ul ales. Hash/decodare/cadre exacte se verifică în renderer înainte de reutilizare. Asamblarea finală și mixul sunt operații separate.')


def verify_material(mid):
    p,m=security.material(mid);failures=[];checked=[]
    for ref in [c['source'] for c in m['timeline']]+m.get('sources',[]):
        try:checked.append(str(core.checked(p,ref)))
        except (ValueError,OSError) as e:failures.append(str(e))
    for scene in m['scenes']:
        for profile in ('landscape','portrait'):
            eff=asset_scenes.effective(scene,profile)
            try:
                core.checked(p,eff['asset']);asset=eff.get('selected_asset')
                if asset and asset.get('provider') not in ('local','graphic','ai-local') and not asset_scenes.provenance_complete(asset):failures.append(f'{scene["id"]}: provenance incompletă')
            except (ValueError,OSError) as e:failures.append(str(e))
    if m.get('alignment'):
        from ..review import bindings
        try:bindings(p,m)
        except (ValueError,OSError) as e:failures.append(str(e))
        cursor=0
        for w in m['alignment']['words']:
            if not cursor<=w['start']<w['end']<=m['frames']:failures.append('Interval alignment invalid.')
            cursor=w['end']
    from ..audio_mix import validate_recipe
    try:validate_recipe(p,m)
    except (ValueError,OSError) as e:failures.append(str(e))
    return dict(technical_status='failed' if failures else 'passed',files_checked=len(set(checked)),failures=failures,
                listening_review='not_listened',editorial_review='not_reviewed',ctc_human_review='pending',visual_sample_review='not_reviewed')


def undo_audio(mid):
    with core.lock():
        p,m=security.material(mid);revisions=sorted((p.parent/'audio-mix-revisions').glob('*/before-material.json'),key=lambda p:p.stat().st_mtime_ns)
        if not revisions:raise ValueError('Nu există revizie audio de restaurat.')
        previous=core.read(revisions[-1]);audit=p.parent/'audio-mix-revisions'/uuid.uuid4().hex
        core.write(audit/'before-material.json',m)
        if 'audio_mix' in previous:m['audio_mix']=previous['audio_mix']
        else:m.pop('audio_mix',None)
        from ..audio_mix import validate_recipe
        validate_recipe(p,m);core.write(audit/'after-material.json',m);core.write(p,m)
    return dict(technical_status='passed',note='Config audio restaurată; master narativ nemodificat.')


def namespace_request(engine,args,base):
    """Normalize nested CLI contracts before calling the same shared dispatcher."""
    if not isinstance(args,list) or not args or any(not isinstance(x,str) for x in args):raise ValueError('args cere o listă de șiruri.')
    try:child=catalog.parsers(engine).parse_args(args)
    except SystemExit as e:raise ValueError('Comandă imbricată invalidă.') from e
    command=[child.command]
    if child.command=='assets':command.append(child.asset_command)
    spec=next((s for s in catalog.catalog(engine) if s['command']==command),None)
    if not spec or not spec['available']:raise ValueError('Comandă imbricată indisponibilă.')
    values={}
    for f in spec['fields']:
        v=getattr(child,f['name'],None)
        if v is None:continue
        if f['kind']=='path':
            def absolute(x):return str(Path(x) if Path(x).is_absolute() else Path(base)/x)
            v=[absolute(x) for x in v] if isinstance(v,list) else absolute(v)
        values[f['name']]=v
    return dict(engine=engine,command=command,values=values)
