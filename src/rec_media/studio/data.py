"""Read-only projections of manifests, outputs and hardware for Studio."""
from pathlib import Path
import hashlib
import json
import os
import shutil
from .. import core, asset_scenes
from . import security, operations, platform_support


def file_url(p):
    from urllib.parse import quote
    try:return '/files?path='+quote(str(security.path(p).relative_to(core.ROOT)))
    except ValueError:return None


def decorate_asset(asset,document):
    a=dict(asset)
    for k in ('local_path','thumbnail_path','preview_path','path'):
        if a.get(k):
            p=core.resolve(document,a[k]);u=file_url(p)
            if u and p.is_file():a[k+'_url']=u
    return a


def materials():
    rows=[]
    for p in sorted((core.ROOT/'materials').glob('*/material.json')):
        try:
            _,m=core.load(p)
            rows.append(dict(id=m['id'],duration=m['frames']/m['sample_rate'],sample_rate=m['sample_rate'],scenes=len(m['scenes']),
                technical_status=m.get('technical_status','not_tested'),alignment_status=m.get('alignment_status','not_aligned'),
                low_confidence=len((m.get('alignment') or {}).get('low_confidence',[])),pending=sum(s.get('review_status')!='APPROVED' for s in m['scenes']),
                exports=len(m.get('exports',[]))))
        except Exception as e:rows.append(dict(id=p.parent.name,error=str(e)))
    return rows


def detail(mid):
    p,m=security.material(mid);result=dict(m);result['manifest_sha256']=core.sha(p)
    result['scenes']=[]
    c=core.config(overrides=m.get('composition',{}))
    for s in m['scenes']:
        scene=dict(s);scene['context']=asset_scenes.context(m,s);scene['effective']={}
        for profile in ('landscape','portrait'):
            eff=asset_scenes.effective(s,profile)
            asset=eff.get('selected_asset') or eff.get('asset',{})
            scene['effective'][profile]=dict(eff,preview_asset=decorate_asset(asset,p))
        scene['alternatives']=[decorate_asset(a,p) for a in s.get('alternatives',[])]
        result['scenes'].append(scene)
    result['audio_url']=None
    if len(m['timeline'])==1 and m['timeline'][0]['start']==0:result['audio_url']=file_url(core.resolve(p,m['timeline'][0]['source']['path']))
    a=m.get('alignment')
    result['alignment_summary']=dict(total_units=len(a.get('words',[])),low_confidence=len(a.get('low_confidence',[])),key=None) if a else None
    if a:
        from ..review import alignment_key
        result['alignment_summary']['key']=alignment_key(m)
    result['effective_config']=c
    result['review_statuses']=dict(technical_status=m.get('technical_status','not_tested'),visual_sample_review=m.get('visual_review_status','not_reviewed'),
        browser_review='not_reviewed',listening_review=m.get('listening_status','not_listened'),editorial_review=m.get('editorial_review_status','not_reviewed'),ctc_human_review='pending')
    return security.public(result)


def outputs(mid=None):
    files=[];roots=[core.ROOT/'output']
    # Include Studio exports without indexing caches, private source trees or incomplete files.
    if (core.ROOT/'work/studio/exports').exists():roots.append(core.ROOT/'work/studio/exports')
    for root in roots:
        for p in root.rglob('*'):
            if not p.is_file() or p.suffix not in security.EXTENSIONS or any(x.startswith('.') for x in p.relative_to(root).parts) or '.part' in p.name:continue
            if mid and mid not in p.parts and not p.name.startswith(mid):continue
            stat=p.stat();report=p.with_suffix('.report.json');r={}
            if p.name.endswith('.report.json'):report=p
            if report.is_file():
                try:r=core.read(report)
                except ValueError:pass
            creation=r.get('created_utc') or r.get('utc')
            origin='report' if creation else 'unknown'
            if not creation and hasattr(stat,'st_birthtime'):
                from datetime import datetime,timezone
                creation=datetime.fromtimestamp(stat.st_birthtime,timezone.utc).isoformat();origin='filesystem_birthtime'
            files.append(dict(path=str(p.relative_to(core.ROOT)),absolute_path=str(p.resolve()),windows_path=platform_support.windows_path(p.resolve()),folder=str(p.parent.relative_to(core.ROOT)),created=creation,created_source=origin,
                media_type='video' if p.suffix in ('.mp4','.mkv','.webm') else 'audio' if p.suffix in ('.wav','.mp3','.flac','.ogg','.m4a') else 'image' if p.suffix in ('.png','.jpg','.jpeg','.webp','.gif') else 'report',
                size=stat.st_size,modified=stat.st_mtime,profile=r.get('profile'),verify_evidence='recorded_report' if r else 'not_verified',
                sha256=r.get('sha256',r.get('output_sha256')),verify_status=r.get('technical_status','not_tested'),url=file_url(p)))
    return sorted(files,key=lambda x:x['modified'],reverse=True)[:300]


def hardware():
    mem={}
    try:mem={line.split(':')[0]:line.split(':')[1].strip() for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemTotal:','MemAvailable:'))}
    except OSError:pass
    try:ffmpeg=core.tool('ffmpeg')
    except ValueError:ffmpeg=None
    return dict(cpu_count=os.cpu_count(),memory=mem,gpu=dict(dxg=Path('/dev/dxg').exists(),dri=Path('/dev/dri').exists(),status='visible_not_validated' if Path('/dev/dxg').exists() or Path('/dev/dri').exists() else 'not_visible',vram='unknown',windows='not_checked'),
        ffmpeg=ffmpeg,piper_interpreter=str(core.ROOT/'.venv/bin/python'),piper_model_present=(core.ROOT/'models/piper/model.lock.json').exists(),
        alignment_present=(core.ROOT/'.venv-align/bin/python').exists(),alignment_model_present=(core.ROOT/'models/alignment/romanian-wav2vec2/model.lock.json').exists(),
        ai_image=dict(status='blocked',reason='image-plan este contract; inferență locală nevalidată.'),ai_video=dict(status='unavailable',reason='Backend opțional neinstalat; fără instalare automată.'),pexels_configured=bool(os.environ.get('PEXELS_API_KEY')))
