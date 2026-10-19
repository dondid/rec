"""Local material model, immutable source references and integer sample timeline."""
import contextlib
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[2]
VERSION = '0.1.0'


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def key(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name('.' + path.name + '.' + uuid.uuid4().hex + '.part')
    with tmp.open('w', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')
    os.replace(tmp, path)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def tool(name):
    # Never mutate audio PATH. Prefer the already-installed local build.
    local = ROOT / '.tools/ffmpeg' / name
    result = local if local.is_file() else shutil.which(name)
    if not result:
        raise ValueError(f'Lipsește {name}; media nu instalează automat unelte.')
    return str(result)


def run(args, cwd=None):
    p = subprocess.run([str(a) for a in args], cwd=cwd, capture_output=True, text=True)
    if p.returncode:
        raise ValueError(f'{args[0]} a eșuat ({p.returncode}): {p.stderr[-3000:]}')
    return p.stdout


def ff(args, cwd=None):
    return run([tool('ffmpeg'), '-nostdin', '-hide_banner', '-v', 'error', '-threads', '2', *args], cwd)


def probe(path):
    return json.loads(run([tool('ffprobe'), '-v', 'error', '-show_streams', '-show_format', '-of', 'json', Path(path).resolve()]))


def config(path=None,overrides=None):
    p = Path(path or ROOT / 'media.json')
    c = read(p)
    c.update(overrides or {})
    font = Path(c['font'])
    c['font'] = str((p.parent / font).resolve()) if not font.is_absolute() else str(font)
    if not font.is_absolute():font = Path(c['font'])
    if not font.is_file():raise ValueError('Font local lipsă.')
    for field, low, high in [('fps',1,60), ('crf',0,40), ('threads',1,4), ('font_min',12,120), ('subtitle_font_size',12,200), ('thumbnail_font_size',12,300), ('title_candidates',1,5), ('title_max_chars',20,300), ('thumbnail_max_chars',10,150)]:
        v=c[field]
        if type(v) is not int or not low <= v <= high:raise ValueError(f'Config invalid: {field}')
    if not isinstance(c['safe_margin'],(float,int)) or not math.isfinite(c['safe_margin']) or not 0.02 <= c['safe_margin'] <= 0.2:raise ValueError('safe_margin invalid')
    if c['fit'] not in ('contain','cover') or c['preset'] not in ('ultrafast','veryfast','medium','slow'):raise ValueError('fit/preset invalid')
    if not re.fullmatch('[0-9A-Fa-f]{6}',c['subtitle_color']):raise ValueError('Culoare subtitrare invalidă')
    for field,default,low,high in [('motion_amount',.04,0,.15),('transition_seconds',.2,.04,2),('title_fade_seconds',.2,0,2),('subtitle_margin_v',.07,.02,.4),('subtitle_outline',3,0,8)]:
        c.setdefault(field,default)
        if type(c[field]) not in (int,float) or not math.isfinite(c[field]) or not low<=c[field]<=high:raise ValueError(f'{field} invalid')
    return c


def profiles(names,c,width=None,height=None):
    result={}
    for name in names.split(','):
        alias={'youtube-landscape':'landscape','shorts-portrait':'portrait'}.get(name,name)
        if name=='custom':size=[width,height]
        else:
            if alias not in c['profiles']:raise ValueError(f'Profil necunoscut: {name}')
            size=c['profiles'][alias]
        if len(size)!=2 or any(type(n) is not int or not 64<=n<=4096 or n%2 for n in size):raise ValueError('Dimensiuni pare între 64 și 4096 necesare.')
        result[name]=list(size)
    if not result:raise ValueError('Niciun profil selectat.')
    return result


def material_path(value):
    p=Path(value)
    if p.is_file():return p.resolve()
    candidate=ROOT/'materials'/str(value)/'material.json'
    if candidate.is_file():return candidate
    raise ValueError(f'Material inexistent: {value}')


def resolve(document,path):
    p=Path(path)
    return p if p.is_absolute() else (Path(document).parent/p).resolve()


def reference(path, document, **extra):
    path=Path(path).resolve()
    return dict(path=os.path.relpath(path,Path(document).parent), sha256=sha(path), **extra)


def checked(document,ref):
    p=resolve(document,ref['path'])
    if not p.is_file() or sha(p)!=ref['sha256']:raise ValueError(f'Sursă lipsă/modificată: {p}')
    return p


def load(value):
    p=material_path(value);m=read(p)
    if m['schema_version']!=1:raise ValueError('Schema material nesuportată.')
    if not isinstance(m['id'],str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}',m['id']):raise ValueError('ID material invalid.')
    if type(m['sample_rate']) is not int or m['sample_rate']<=0 or type(m['frames']) is not int or m['frames']<=0:raise ValueError('Cronologie invalidă.')
    cursor=0
    for clip in m['timeline']:
        if any(type(clip[k]) is not int for k in ('timeline_start','start','end')) or clip['start']<0 or clip['timeline_start']!=cursor or clip['end']<=clip['start']:raise ValueError('Cronologie cu gol/suprapunere sau eșantioane invalide.')
        cursor+=clip['end']-clip['start']
    if cursor!=m['frames']:raise ValueError('Acoperire audio invalidă.')
    return p,m


def new_path(identifier):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}',identifier):raise ValueError('ID: litere ASCII, cifre, - și _, maximum 80.')
    p=ROOT/'materials'/identifier/'material.json'
    if p.parent.exists():raise ValueError(f'Material existent: {identifier}')
    return p


def statuses():
    return dict(technical_status='not_tested',alignment_status='not_aligned',visual_review_status='not_reviewed',listening_status='not_listened',editorial_review_status='not_reviewed')


def base(identifier, rate, frames, text='', displayed=None):
    return dict(schema_version=1,id=identifier,created_utc=now(),parents=[],sources=[],sample_rate=rate,frames=frames,
                text_original=text,text_display=text if displayed is None else displayed,text_spoken=text,
                timeline=[],text_units=[],alignment=None,scenes=[],titles={'candidates':[],'selected':None,'locked':False},
                thumbnail_text=None,profiles={},composition={},pronunciation_rules=[],exports=[],history=[],**statuses())


def init(identifier, audio, text=None, image=None, tts_report=None):
    p=new_path(identifier); audio=Path(audio).resolve()
    info=probe(audio); streams=[s for s in info['streams'] if s['codec_type']=='audio']
    if len(streams)!=1:raise ValueError('Intrarea trebuie să conțină un singur stream audio.')
    rate=int(streams[0]['sample_rate'])
    original=Path(text).read_text(encoding='utf-8-sig') if text else ''
    spoken=original; manifest=None; report=None
    if tts_report:
        report=read(tts_report)
        if report['output_sha256']!=sha(audio):raise ValueError('Raport TTS pentru alt audio.')
        if text and report['source_sha256']!=sha(text):raise ValueError('Raport TTS pentru altă versiune a textului.')
        manifest=read(resolve(tts_report,report['manifest']))
        spoken=''.join(s['spoken']+s['separator'] for s in manifest['segments'])
    p.parent.mkdir(parents=True)
    pcm=p.parent/'source.wav'
    ff(['-i',audio,'-map','0:a:0','-ac','1','-ar',str(rate),'-c:a','pcm_s32le','-rf64','auto',pcm])
    decoded=probe(pcm)['streams'][0]
    frames=int(decoded['duration_ts'])
    m=base(identifier,rate,frames,original)
    m['text_spoken']=spoken
    m['sources']=[reference(audio,p,role='original_audio',media=info)]
    if text:m['sources'].append(reference(text,p,role='original_text'))
    if tts_report:m['sources'].append(reference(tts_report,p,role='tts_report'))
    pcm_ref=reference(pcm,p)
    m['timeline']=[dict(source=pcm_ref,start=0,end=frames,timeline_start=0)]
    if spoken:m['text_units']=[dict(start=0,end=frames,spoken=spoken,display=m['text_display'],timing='document_only')]
    if image:m['scenes']=[dict(id='scene-001',start=0,end=frames,asset=reference(image,p),kind='image',anchor=spoken,motion='none',transition='cut',focal=[0.5,0.5],profiles={})]
    elif any(s['codec_type']=='video' for s in info['streams']):
        m['scenes']=[dict(id='source-video',start=0,end=frames,asset=reference(audio,p,license='unknown'),kind='video',anchor=spoken,motion='none',transition='cut',focal=[.5,.5],profiles={})]
    if manifest:
        m['pronunciation_rules']=manifest['replacements']
        m['history'].append(dict(action='import_tts',manifest=reference(resolve(tts_report,report['manifest']),p),note='Limitele segmentelor nu sunt timpi de cuvinte.'))
    m['technical_status']='passed';write(p,m)
    return p,m


@contextlib.contextmanager
def lock():
    p=ROOT/'work/media/project.lock';p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('a') as f:
        try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('Alt proces media scrie proiectul.')
        yield


def assemble(document,m,dest):
    """Stream PCM from frame-exact source intervals, with no resampling/effects."""
    import wave
    dest=Path(dest);dest.parent.mkdir(parents=True,exist_ok=True)
    # Internal PCM sources are 32-bit mono; RF64 output is produced by FFmpeg.
    raw=dest.with_suffix('.pcm.part')
    with raw.open('wb') as out:
        for clip in m['timeline']:
            source=checked(document,clip['source'])
            # FFmpeg trims in source sample indices, not approximate timestamps.
            temp=dest.with_name(dest.name+'.clip.pcm')
            ff(['-i',source,'-af',f"atrim=start_sample={clip['start']}:end_sample={clip['end']},asetpts=PTS-STARTPTS",'-f','s32le','-ac','1','-ar',str(m['sample_rate']),temp])
            with temp.open('rb') as f:shutil.copyfileobj(f,out,1024*1024)
            temp.unlink()  # Only this invocation's generated intermediate.
    if raw.stat().st_size!=m['frames']*4:raise ValueError('Acoperirea eșantioanelor PCM este incompletă.')
    ff(['-f','s32le','-ar',str(m['sample_rate']),'-ac','1','-i',raw,'-c:a','pcm_s32le','-rf64','auto',dest])
    return dest
