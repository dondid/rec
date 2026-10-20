"""Project-scoped file access and request validation. Never a shell interface."""
from pathlib import Path
import re
from .. import core

DIRECTORIES = ('materials', 'input', 'samples', 'assets', 'output', 'work', 'models')
EXTENSIONS = {'.json', '.txt', '.md', '.png', '.jpg', '.jpeg', '.webp', '.gif', '.mp4', '.mkv', '.webm', '.wav', '.mp3', '.flac', '.ogg', '.m4a', '.srt', '.ass', '.html', '.log'}


def path(value, *, exists=False, directory=False):
    if not isinstance(value, (str, Path)) or not str(value) or '\x00' in str(value):
        raise ValueError('Cale locală invalidă.')
    p = Path(value)
    p = (core.ROOT / p).resolve() if not p.is_absolute() else p.resolve()
    roots = [(core.ROOT / name).resolve() for name in DIRECTORIES]
    special = [core.ROOT / n for n in ('media.json', 'rec.json', 'pronunciations.json')]
    if p not in special and not any(p.is_relative_to(r) for r in roots):
        raise ValueError('Calea este în afara directoarelor permise ale proiectului.')
    if any(part.startswith('.') for part in p.relative_to(core.ROOT).parts):
        raise ValueError('Fișierele ascunse nu sunt accesibile în Studio.')
    if exists and not p.exists():raise ValueError('Fișier/director inexistent.')
    if directory and p.exists() and not p.is_dir():raise ValueError('Este necesar un director.')
    return p


def identifier(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}',value):
        raise ValueError('ID invalid.')
    return value


def material(value):
    identifier(value)
    p = path(f'materials/{value}/material.json', exists=True)
    return core.load(p)


def public(value):
    """Redact secrets in diagnostics, including unexpected nested provider data."""
    if isinstance(value,dict):
        return {k: ('[REDACTED]' if any(x in k.lower() for x in ('api_key','apikey','authorization','password','secret','token')) else public(v)) for k,v in value.items()}
    if isinstance(value,list):return [public(v) for v in value]
    if isinstance(value,str):
        import os
        secret=os.environ.get('PEXELS_API_KEY')
        if secret:value=value.replace(secret,'[REDACTED]')
    return value


def validate_references(value, base):
    """Validate nested file contracts before they reach the trusted CLI services."""
    if isinstance(value,list):
        for v in value:validate_references(v,base)
    elif isinstance(value,dict):
        for k,v in value.items():
            if k in ('path','local_path','font') and isinstance(v,str) and v:
                p=Path(v);p=p if p.is_absolute() else Path(base).parent/p
                if k=='font' and p.resolve().is_relative_to(Path('/usr/share/fonts')) and p.is_file():continue
                path(p)
            validate_references(v,base)


def media_file(value):
    """Reject playlists/indirections before any legacy FFmpeg command sees them."""
    p=path(value,exists=True)
    if not p.is_file():raise ValueError('Fișier media necesar.')
    with p.open('rb') as f:head=f.read(64)
    supported=(head.startswith((b'RIFF',b'RF64')) and head[8:12]==b'WAVE') or head.startswith((b'fLaC',b'OggS',b'ID3',b'\x89PNG\r\n\x1a\n',b'\xff\xd8\xff',b'GIF87a',b'GIF89a',b'\x1aE\xdf\xa3')) or (head.startswith(b'RIFF') and head[8:12]==b'WEBP') or head[4:8]==b'ftyp' or (len(head)>1 and head[0]==255 and head[1]&224==224)
    if not supported:raise ValueError('Container local nerecunoscut; playlisturile/URL-urile și fișierele indirecte nu sunt permise.')
    return p
