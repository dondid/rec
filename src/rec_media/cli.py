import argparse
import contextlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import uuid

from .core import ROOT,VERSION,config,ff,key,load,lock,now,probe,read,reference,resolve,sha,tool,write


def doctor():
    from PIL import __version__ as pillow_version
    c=config();filters=ff(['-filters']);encoders=ff(['-encoders'])
    needed=['scale','pad','crop','ass','overlay','zoompan','xfade','concat','atrim','tpad']
    available={n:bool(re.search(r'\s'+n+r'\s',filters)) for n in needed}
    result=dict(created_utc=now(),version=VERSION,python=sys.version,pillow=pillow_version,cpu_count=os.cpu_count(),
                memory={line.split(':')[0]:line.split(':')[1].strip() for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemTotal:','MemAvailable:'))},
                free_bytes=shutil.disk_usage(ROOT).free,gpu=dict(dxg=Path('/dev/dxg').exists(),dri=Path('/dev/dri').exists(),nvidia_smi=shutil.which('nvidia-smi'),status='not_visible'),
                ffmpeg=tool('ffmpeg'),ffprobe=tool('ffprobe'),ffmpeg_version=ff(['-version']).splitlines()[0],filters=available,
                h264='libx264' in encoders,aac=bool(re.search(r'\saac\s',encoders)),font=dict(path=c['font'],sha256=sha(c['font'])),
                optional_backends={n:'optional_not_installed' for n in ['whisperx_ro','qwen_llama_cpp','wan21']})
    folder=ROOT/'work/media/doctor'/uuid.uuid4().hex;folder.mkdir(parents=True)
    if result['gpu']['dxg'] or result['gpu']['dri'] or result['gpu']['nvidia_smi']:result['gpu']['status']='visible_not_validated'
    interpreter=ROOT/'.venv-align/bin/python'
    model=ROOT/'models/alignment/romanian-wav2vec2'
    result['alignment_backend']={'backend':'ctc-ro','installed':interpreter.exists(),'model_present':(model/'model.lock.json').exists(),'device':'cpu'}
    if interpreter.exists() and (model/'model.lock.json').exists():
        from .alignment import model_identity
        identity=model_identity(model)
        result['alignment_backend'].update(model_checksums='passed',revision=identity['revision'])
    test=folder/'encode.mp4'
    ff(['-f','lavfi','-i','color=c=blue:s=64x64:r=30:d=0.1','-f','lavfi','-i','anullsrc=r=22050:cl=mono','-t','0.1','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',test])
    ff(['-xerror','-i',test,'-f','null','-'])
    result['encode_test']=str(test);result['technical_status']='passed' if all(available.values()) and result['h264'] and result['aac'] else 'failed'
    write(folder/'report.json',result)
    return result


def parser():
    p=argparse.ArgumentParser(description='REC media local CPU; fără descărcări la procesare.')
    p.add_argument('--config',type=Path,default=ROOT/'media.json')
    p.add_argument('--report',type=Path)
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor')
    s=sub.add_parser('audio-mix');s.add_argument('material');s.add_argument('--output-dir',type=Path);s.add_argument('--output',type=Path)
    s.add_argument('--mux-video',type=Path,help='Copiază streamul video existent; schimbă numai audio')
    actions=s.add_mutually_exclusive_group(required=True)
    actions.add_argument('--inspect',action='store_true');actions.add_argument('--validate',type=Path)
    actions.add_argument('--set',type=Path);actions.add_argument('--disable',action='store_true')
    actions.add_argument('--render',action='store_true');actions.add_argument('--verify',type=Path)
    s=sub.add_parser('image-plan');s.add_argument('request',type=Path);s.add_argument('--output',required=True,type=Path)
    s=sub.add_parser('workflow');s.add_argument('plan',type=Path);s.add_argument('--only',nargs='+');s.add_argument('--disable',nargs='+');s.add_argument('--rerun',nargs='+')
    s=sub.add_parser('synthesize-parts');s.add_argument('manifest',type=Path);s.add_argument('--output-dir',required=True,type=Path);s.add_argument('--apply',action='store_true')
    s=sub.add_parser('split-text');s.add_argument('text',type=Path);s.add_argument('--output-dir',required=True,type=Path)
    method=s.add_mutually_exclusive_group(required=True)
    method.add_argument('--parts',type=int);method.add_argument('--target-duration',type=float);method.add_argument('--chapters',action='store_true');method.add_argument('--delimiter');method.add_argument('--manual-ranges',type=Path);method.add_argument('--semantic',action='store_true')
    s.add_argument('--words-per-minute',type=float,default=150)
    s=sub.add_parser('merge-text');s.add_argument('manifest',type=Path);s.add_argument('--output',required=True,type=Path)
    s=sub.add_parser('init');s.add_argument('--id',required=True);s.add_argument('--audio',required=True,type=Path);s.add_argument('--text',type=Path);s.add_argument('--image',type=Path);s.add_argument('--tts-report',type=Path);s.add_argument('--sample-rate',type=int)
    s=sub.add_parser('convert-narration');s.add_argument('material');s.add_argument('--id',required=True);s.add_argument('--sample-rate',type=int,default=22050)
    s=sub.add_parser('compile');s.add_argument('--id',required=True);s.add_argument('--materials',required=True,nargs='+');s.add_argument('--composition',required=True,type=Path);s.add_argument('--plan-only',action='store_true')
    s=sub.add_parser('compile-video');s.add_argument('material');s.add_argument('--videos',required=True,type=Path);s.add_argument('--output',required=True,type=Path);s.add_argument('--profiles',default='portrait')
    s=sub.add_parser('align');s.add_argument('material')
    backend=s.add_mutually_exclusive_group(required=True)
    backend.add_argument('--words',type=Path);backend.add_argument('--backend',choices=['ctc-ro'])
    s.add_argument('--provenance');s.add_argument('--model',type=Path);s.add_argument('--windows',type=Path);s.add_argument('--max-windows',type=int);s.add_argument('--segments',help='Indici CTC de la zero, separați prin virgulă')
    s=sub.add_parser('alignment-review');s.add_argument('material');s.add_argument('--output',type=Path);s.add_argument('--apply',type=Path);s.add_argument('--validate',type=Path);s.add_argument('--media',type=Path)
    s=sub.add_parser('scene-plan');s.add_argument('material');s.add_argument('--output',required=True,type=Path);assets=s.add_mutually_exclusive_group(required=True);assets.add_argument('--folder',type=Path);assets.add_argument('--images',type=Path,nargs='+');s.add_argument('--intervals',type=Path)
    s=sub.add_parser('scenes');s.add_argument('material');s.add_argument('--scene');s.add_argument('--profile',choices=['landscape','portrait','custom','square']);s.add_argument('--library-root',type=Path)
    action=s.add_mutually_exclusive_group()
    action.add_argument('--plan',type=Path);action.add_argument('--inspect',action='store_true');action.add_argument('--alternatives',action='store_true')
    action.add_argument('--select');action.add_argument('--replace',type=Path);action.add_argument('--remove',action='store_true');action.add_argument('--restore',action='store_true');action.add_argument('--set',type=Path);action.add_argument('--auto',action='store_true');action.add_argument('--sequence',type=Path)
    s.add_argument('--approve',action='store_true');s.add_argument('--allow-unknown-license',action='store_true')
    s=sub.add_parser('assets');s.add_argument('--library-root',type=Path)
    actions=s.add_subparsers(dest='asset_command',required=True)
    a=actions.add_parser('search');a.add_argument('material');a.add_argument('--scene',required=True);a.add_argument('--provider',nargs='+',choices=['commons','openverse','pexels'],default=['commons','openverse']);a.add_argument('--query');a.add_argument('--type',choices=['image','video'],default='image');a.add_argument('--limit',type=int,default=8);a.add_argument('--mode',choices=['manual','assisted','auto'],default='assisted')
    a=actions.add_parser('queries');a.add_argument('material');a.add_argument('--scene',required=True)
    a=actions.add_parser('list');a.add_argument('--query',default='');a.add_argument('--type',choices=['image','video']);a.add_argument('--filters',type=Path)
    a=actions.add_parser('import');a.add_argument('path',type=Path);a.add_argument('--metadata',type=Path)
    a=actions.add_parser('download');a.add_argument('material');a.add_argument('--scene',required=True);d=a.add_mutually_exclusive_group(required=True);d.add_argument('--candidate');d.add_argument('--all',action='store_true');a.add_argument('--rendition',choices=['original','thumbnail'],default='original')
    a=actions.add_parser('review');a.add_argument('material');a.add_argument('--output-dir',required=True,type=Path)
    a=actions.add_parser('credits');a.add_argument('material');a.add_argument('--output-dir',type=Path);a.add_argument('--profiles',help='Profile efectiv publicate, separate prin virgulă')
    s=sub.add_parser('titles');s.add_argument('material');s.add_argument('--manual');s.add_argument('--select');s.add_argument('--approve',action='store_true');s.add_argument('--unlock',action='store_true');s.add_argument('--candidates',type=int)
    for name in ['subtitles','thumbnail','render']:
        s=sub.add_parser(name);s.add_argument('material');s.add_argument('--profiles',default='landscape');s.add_argument('--width',type=int);s.add_argument('--height',type=int)
        if name=='subtitles':
            s.add_argument('--mode',choices=['classic','highlight','scroll'],default='classic');s.add_argument('--output-dir',required=True,type=Path)
            s.add_argument('--ass-preset',choices=['safe','boxed','minimal'])
        elif name=='thumbnail':
            s.add_argument('--text');s.add_argument('--image',type=Path);s.add_argument('--scene');s.add_argument('--variant',choices=['panel','top'],default='panel');s.add_argument('--format',choices=['png','jpeg'],default='png');s.add_argument('--output-dir',required=True,type=Path)
        else:
            s.add_argument('--image',type=Path);s.add_argument('--subtitles',choices=['off','classic','highlight','scroll'],default='off');s.add_argument('--title');s.add_argument('--force',action='store_true');s.add_argument('--plan-only',action='store_true')
            s.add_argument('--ass-preset',choices=['safe','boxed','minimal'])
            s.add_argument('--rerender-changed',action='store_true',help='Cu --resume-run: păstrează intermediarii anteriori și recalculează numai scenele schimbate')
            s.add_argument('--resume-run',help='Reia un run cu scene verificate prin receipts/hash, fără rerandare')
            s.add_argument('--output-root',type=Path,help='Rădăcină alternativă; exportă în <root>/<material>/<profil>/video.mp4')
    s=sub.add_parser('split');s.add_argument('material');s.add_argument('--mode',choices=['partition','extract'],default='partition');s.add_argument('--intervals',type=Path);s.add_argument('--parts',type=int);s.add_argument('--target-seconds',type=float);s.add_argument('--max-seconds',type=float,help='Plafon strict în eșantioane; conflict explicit dacă limitele nu îl respectă');s.add_argument('--prefix',required=True);s.add_argument('--apply',action='store_true')
    s=sub.add_parser('merge');s.add_argument('--id',required=True);s.add_argument('--materials',required=True,nargs='+');s.add_argument('--plan-only',action='store_true');s.add_argument('--composition',type=Path)
    s=sub.add_parser('batch');s.add_argument('file',type=Path)
    s=sub.add_parser('verify');s.add_argument('video',type=Path)
    return p


def execute(a):
    from .core import init,profiles
    from . import content,video,derive
    c=config(a.config)
    if getattr(a,'material',None):
        _,material=load(a.material)
        c=config(a.config,material.get('composition',{}))
        # Revalidate inherited numeric settings with the same checks as project config.
        for name in ('fps','crf','threads'):
            if type(c[name]) is not int:raise ValueError(f'{name} trebuie să fie întreg.')
        if not 1<=c['fps']<=60 or not 0<=c['crf']<=40 or not 1<=c['threads']<=4:raise ValueError('Setări material invalide.')
    if a.command=='doctor':return doctor()
    if a.command in ('convert-narration','compile','compile-video') or (a.command=='merge' and a.composition):
        from . import compilation
        if a.command=='convert-narration':return {'material':compilation.convert_material(a.material,a.id,a.sample_rate),'technical_status':'passed'}
        if a.command=='compile-video':
            sizes=profiles(a.profiles,c)
            if len(sizes)!=1:raise ValueError('compile-video exportă un singur profil per output.')
            return compilation.video(a.material,read(a.videos),a.output,a.videos,next(iter(sizes.values())),c['fps'])
        result=compilation.create(a.materials,a.id,read(a.composition),a.composition,a.plan_only)
        return result if isinstance(result,dict) else dict(material=result,technical_status='passed')
    if a.command=='audio-mix':
        from . import audio_mix
        p,m=load(a.material)
        if a.inspect:
            audio_mix.validate_recipe(p,m)
            return dict(narration=dict(type='narration',immutable_source=True,timeline=m['timeline']),sample_rate=m['sample_rate'],channels=1,frames=m['frames'],audio_mix=m.get('audio_mix',dict(enabled=False)),fingerprint=audio_mix.fingerprint(p,m))
        if a.validate or a.set:
            path=a.validate or a.set;spec=audio_mix.configure(p,m,read(path),path)
            if a.set:
                audit=p.parent/'audio-mix-revisions'/uuid.uuid4().hex
                audit.mkdir(parents=True);shutil.copy2(p,audit/'before-material.json');write(audit/'imported-config.json',read(path))
                m['audio_mix']=spec
                write(p,m);write(audit/'after-material.json',m)
            return dict(technical_status='passed',validation_only=bool(a.validate),audio_mix=spec)
        if a.disable:
            write(p.parent/'audio-mix-revisions'/uuid.uuid4().hex/'before-material.json',m)
            m.setdefault('audio_mix',{})['enabled']=False;write(p,m)
            return dict(technical_status='passed',enabled=False)
        if a.verify:return audio_mix.verify(a.verify,m['sample_rate'],m['frames'])
        if not a.output_dir and not a.mux_video:raise ValueError('--render cere --output-dir sau --mux-video + --output.')
        if a.mux_video:
            if not a.output:raise ValueError('--mux-video cere --output nou.')
            return audio_mix.mux(p,m,a.mux_video,a.output)
        if a.output_dir.exists():raise ValueError('Director audio mix existent; alege altul.')
        mixed,report=audio_mix.render(p,m)
        a.output_dir.mkdir(parents=True)
        # Published cache entry is verified before the user-facing copy.
        target=a.output_dir/'mix.wav';temporary=a.output_dir/('.'+uuid.uuid4().hex+'.part.wav')
        shutil.copyfile(mixed,temporary);os.replace(temporary,target)
        write(a.output_dir/'mix.report.json',report)
        return dict(technical_status='passed',path=str(target.resolve()),report=report)
    if a.command=='image-plan':
        from .backends import image_plan
        return image_plan(a.request,a.output)
    if a.command=='workflow':
        from .workflow import run
        return run(a.plan,a.only,a.disable,a.rerun)
    if a.command=='synthesize-parts':
        from .workflow import synthesize_parts
        return synthesize_parts(a.manifest,a.output_dir,a.apply)
    if a.command=='split-text':
        from . import text_parts
        return text_parts.split(a.text,a.output_dir,a.parts,a.target_duration,a.chapters,a.delimiter,a.manual_ranges,a.semantic,a.words_per_minute)
    if a.command=='merge-text':
        from . import text_parts
        return text_parts.merge(a.manifest,a.output)
    if a.command=='init':
        p,m=init(a.id,a.audio,a.text,a.image,a.tts_report,a.sample_rate)
        return dict(material=str(p),frames=m['frames'],sample_rate=m['sample_rate'],timeline_hash=key(m['timeline']),technical_status='passed')
    if a.command=='align':
        if a.words:
            if not a.provenance:raise ValueError('Importul manual cere --provenance.')
            if a.model or a.windows or a.max_windows or a.segments:raise ValueError('Opțiunile backend-ului nu se aplică importului manual.')
            return content.import_alignment(a.material,a.words,a.provenance)
        import unicodedata
        normalize=lambda text:unicodedata.normalize('NFC',text).translate(str.maketrans('şţŞŢ','șțȘȚ')).split()
        if normalize(material['text_display'])!=normalize(material['text_spoken']):
            raise ValueError('Afișarea diferă de rostire; furnizează maparea explicită prin --words/display_group. Nu se deduce automat.')
        alphabet=set('abcdefghijklmnopqrstuvwxyzăâîșț')
        unsupported=sorted({ch for ch in material['text_spoken'].lower().translate(str.maketrans('şţ','șț')) if ch.isalpha() and ch not in alphabet})
        if unsupported:raise ValueError('Caractere fără suport în modelul CTC: '+', '.join(unsupported)+'. Cuvintele nu primesc timpi inventați.')
        from .alignment import launch
        return launch(a.material,a.model,a.windows,a.max_windows,[int(i) for i in a.segments.split(',')] if a.segments else None)
    if a.command=='alignment-review':
        from . import review
        if sum(bool(v) for v in (a.output,a.apply,a.validate))!=1:raise ValueError('Alege --output, --validate sau --apply.')
        return review.apply(a.material,a.apply or a.validate,validate_only=bool(a.validate)) if a.apply or a.validate else review.report(a.material,a.output,a.media)
    if a.command=='scene-plan':
        from .scenes import propose
        return propose(a.material,a.output,a.folder,a.images,a.intervals)
    if a.command=='assets':
        from . import asset_scenes,asset_library
        command=a.asset_command
        if command=='search':return asset_scenes.search(a.material,a.scene,a.provider,a.query,a.type,a.limit,a.mode,a.library_root)
        if command=='queries':
            _,m=load(a.material);scene=asset_scenes.find(m,a.scene)
            proposed=asset_scenes.queries(asset_scenes.context(m,scene))
            proposed.update({k:v for k,v in scene.get('curated_query',{}).items() if k in ('query_ro','query_en')})
            if scene.get('curated_query'):proposed['query_override_source']='scene.curated_query'
            return proposed
        if command=='list':
            with asset_library.Library(a.library_root) as library:return dict(assets=library.records(a.query,a.type,**(read(a.filters) if a.filters else {})))
        if command=='import':
            with asset_library.Library(a.library_root) as library:return library.ingest(a.path,read(a.metadata) if a.metadata else None)
        if command=='download':return asset_scenes.download(a.material,a.scene,a.candidate,a.all,a.library_root,a.rendition)
        if command=='review':return asset_scenes.review(a.material,a.output_dir)
        if command=='credits':
            selected_profiles=a.profiles.split(',') if a.profiles else None
            if selected_profiles is not None and (len(set(selected_profiles))!=len(selected_profiles) or any(x not in ('landscape','portrait','custom','square') for x in selected_profiles)):raise ValueError('Profile credits invalide.')
            return asset_scenes.credits(a.material,a.output_dir,profiles=selected_profiles)
    if a.command=='scenes':
        from . import asset_scenes
        if a.plan:return {'scenes':video.import_scenes(a.material,a.plan)}
        if a.sequence:
            if not a.scene:raise ValueError('--scene necesar pentru secvență.')
            return asset_scenes.sequence(a.material,a.scene,a.sequence,a.approve,a.allow_unknown_license,a.library_root)
        if a.select or a.replace or a.remove or a.restore or a.set or a.auto:
            if not a.scene:raise ValueError('--scene este necesar pentru editare.')
            return asset_scenes.select(a.material,a.scene,a.select,a.replace,a.profile,a.approve,a.allow_unknown_license,a.restore,a.remove,read(a.set) if a.set else None,a.library_root,a.auto)
        _,m=load(a.material)
        if a.scene:
            scene=asset_scenes.find(m,a.scene)
            return {'alternatives':scene.get('alternatives',[])} if a.alternatives else {'scene':scene}
        return {'scenes':m['scenes']}
    if a.command=='titles':
        if a.candidates is not None:
            if not 1<=a.candidates<=5:raise ValueError('Între 1 și 5 variante.')
            c['title_candidates']=a.candidates
        return content.titles(a.material,c,a.manual,a.select,a.approve,a.unlock)
    if a.command in ('subtitles','thumbnail','render'):
        if getattr(a,'ass_preset',None):c['subtitle_style']=dict(c.get('subtitle_style',{}),preset=a.ass_preset)
        selected=profiles(a.profiles,c,a.width,a.height)
        if a.command=='render':return video.render(a.material,selected,c,a.image,a.subtitles,a.title,a.force,a.plan_only,a.output_root,a.resume_run,a.rerender_changed)
        if a.output_dir.exists():raise ValueError('Director de export existent; alege altul.')
        if a.command=='thumbnail':
            if not a.image and any(s.get('asset_schema') for s in material['scenes']):
                from .asset_scenes import thumbnail
                return {'outputs':thumbnail(a.material,a.output_dir,selected,c,a.text,a.scene,a.variant,a.format)}
            return {'outputs':content.thumbnail(a.material,a.output_dir,selected,c,a.text,a.image,a.scene,a.variant,a.format)}
        p,m=load(a.material)
        from .subtitles import subtitle_files
        return {name:subtitle_files(p,m,a.output_dir/name,size,c,a.mode,name) for name,size in selected.items()}
    if a.command=='verify':return video.verify(a.video)
    if a.command=='split':
        p,m,plan=derive.split_plan(a.material,a.mode,read(a.intervals) if a.intervals else None,a.parts,a.target_seconds,a.max_seconds)
        folder=ROOT/'work/media/plans'/uuid.uuid4().hex;write(folder/'split-plan.json',plan)
        result={'plan':str(folder/'split-plan.json'),'intervals':plan['intervals'],'technical_status':'planned'}
        if a.apply:result.update(materials=derive.apply_split(a.material,plan,a.prefix),technical_status='passed')
        return result
    if a.command=='merge':
        result=derive.merge(a.materials,a.id,a.plan_only)
        folder=ROOT/'work/media/plans'/uuid.uuid4().hex
        write(folder/'merge-plan.json',result if a.plan_only else {'material':result})
        return dict(result=result,plan=str(folder/'merge-plan.json'),technical_status='planned' if a.plan_only else 'passed')
    if a.command=='batch':
        from PIL import __version__ as pillow_version
        jobs=read(a.file)['jobs'];results=[];state_path=ROOT/'work/media/batches'/(key(jobs)+'.json')
        old=read(state_path) if state_path.exists() else {'jobs':[]}
        for i,job in enumerate(jobs):
            args=job['args']
            if not isinstance(args,list) or any(not isinstance(x,str) for x in args):raise ValueError('Job args trebuie să fie listă de șiruri.')
            try:
                child=parser().parse_args(args)
                if child.command not in ('render','thumbnail','subtitles','titles'):
                    raise ValueError('Loturile acceptă render, thumbnail, subtitles și titles; importul/derivarea se planifică separat.')
                mp,mm=load(child.material)
                input_state={k:v for k,v in mm.items() if k not in ('exports',)}
                if child.command in ('subtitles','thumbnail','titles'):input_state.pop('audio_mix',None)
                fingerprint=key(dict(args=args,pillow=pillow_version,ffmpeg_sha256=sha(tool('ffmpeg')),implementation={p.name:sha(p) for p in Path(__file__).parent.glob('*.py')},material=input_state,config=read(child.config),
                                     assets={str(resolve(mp,s['asset']['path'])):sha(resolve(mp,s['asset']['path'])) for s in mm['scenes']}))
            except (Exception,SystemExit) as e:
                results.append(dict(index=i,technical_status='failed',error=str(e)))
                write(state_path,dict(created_utc=now(),jobs=results))
                continue
            # Retry operations. Render performs content+output-hash validation itself;
            # completed metadata/thumbnail jobs are skipped only with matching recorded file hashes.
            previous=next((j for j in old['jobs'] if j['index']==i and j.get('technical_status')=='passed'),None)
            if previous and previous.get('input_key')==fingerprint and previous.get('artifacts') and all(Path(p).is_file() and sha(p)==h for p,h in previous['artifacts'].items()):
                results.append(dict(previous,resumed=True));continue
            try:
                result=execute(child);artifacts={}
                if child.command in ('thumbnail','render'):
                    paths=result.get('outputs',[])
                    for item in paths:
                        p=item['path'] if isinstance(item,dict) else item
                        artifacts[str(Path(p).resolve())]=sha(p)
                if child.command=='subtitles':
                    artifacts={str(p.resolve()):sha(p) for p in child.output_dir.rglob('*') if p.is_file()}
                if child.command=='titles':
                    artifacts={str(mp.parent/'titles.json'):sha(mp.parent/'titles.json')}
                    _,updated=load(mp)
                    input_state={k:v for k,v in updated.items() if k!='exports'}
                    input_state.pop('audio_mix',None)
                    fingerprint=key(dict(args=args,pillow=pillow_version,ffmpeg_sha256=sha(tool('ffmpeg')),implementation={p.name:sha(p) for p in Path(__file__).parent.glob('*.py')},material=input_state,config=read(child.config),
                                         assets={str(resolve(mp,s['asset']['path'])):sha(resolve(mp,s['asset']['path'])) for s in updated['scenes']}))
                record=dict(index=i,technical_status=result.get('technical_status','passed') if isinstance(result,dict) else 'passed',result=result,artifacts=artifacts,input_key=fingerprint)
            except Exception as e:record=dict(index=i,technical_status='failed',error=str(e))
            results.append(record);write(state_path,dict(created_utc=now(),jobs=results))
        return dict(technical_status='passed' if all(j['technical_status']=='passed' for j in results) else 'failed',jobs=results,state=str(state_path))
    raise ValueError('Comandă necunoscută.')


def main(argv=None):
    a=parser().parse_args(argv)
    try:
        with (contextlib.nullcontext() if a.command=='workflow' else lock()):result=execute(a)
        if a.report:write(a.report,result)
        print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
        return 1 if isinstance(result,dict) and result.get('technical_status') in ('failed','blocked') else 0
    except KeyboardInterrupt:
        print('Întrerupt; exporturile valide sunt păstrate. Repetă comanda.',file=sys.stderr);return 130
    except Exception as e:
        print(f'Eroare media: {e}',file=sys.stderr);return 1
