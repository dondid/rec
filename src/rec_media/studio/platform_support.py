"""Read-only WSL/Windows presentation and fixed toolchain diagnostics."""
from pathlib import Path
import json
import os
import platform
import shutil
import subprocess
from .. import core
from . import security


def windows_path(path,distro=None):
    p=Path(path);parts=p.parts
    if len(parts)>=3 and parts[1]=='mnt' and len(parts[2])==1 and parts[2].isalpha():
        return parts[2].upper()+':\\'+'\\'.join(parts[3:])
    distro=distro or os.environ.get('WSL_DISTRO_NAME')
    if distro and all(c.isalnum() or c in '-_.' for c in distro) and p.is_absolute():return '\\\\wsl.localhost\\'+distro+'\\'+'\\'.join(parts[1:])
    return None


def paths(value):
    p=security.path(value)
    return dict(path=str(p),relative_path=str(p.relative_to(core.ROOT)),windows_path=windows_path(p),windows_path_status='derived_not_opened',
                wsl=bool(os.environ.get('WSL_DISTRO_NAME') or 'microsoft' in platform.release().lower()))


def open_folder(value):
    p=security.path(value,exists=True,directory=True);presentation=paths(p)
    opener=shutil.which('explorer.exe') or shutil.which('xdg-open')
    if not opener:return dict(**presentation,opened=False,status='unavailable',reason='Opener indisponibil; copiază calea Windows/WSL.')
    argument=str(p)
    if opener.lower().endswith('explorer.exe'):
        converter=shutil.which('wslpath')
        if converter:
            converted=subprocess.run([converter,'-w',str(p)],capture_output=True,text=True,timeout=5)
            if converted.returncode==0:argument=converted.stdout.strip()
            elif not presentation['windows_path']:return dict(**presentation,opened=False,status='conversion_failed',reason=converted.stderr[-1000:])
            else:argument=presentation['windows_path']
        elif presentation['windows_path']:argument=presentation['windows_path']
        else:return dict(**presentation,opened=False,status='conversion_unavailable',reason='Nu există conversie Windows; copiază calea WSL.')
    try:
        process=subprocess.Popen([opener,argument],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:code=process.wait(timeout=.6)
        except subprocess.TimeoutExpired:code=None
        if code not in (None,0) and not opener.lower().endswith('explorer.exe'):return dict(**presentation,opened=False,status='opener_failed',pid=process.pid,returncode=code,reason='Opener-ul nu a putut deschide folderul; verifică interop Windows/WSL sau copiază calea afișată.')
        return dict(**presentation,opened=None,status='launch_requested',pid=process.pid,returncode=code,reason='Lansare solicitată; returncode-ul Explorer nu confirmă fereastra. Verifică vizual sau copiază calea afișată.')
    except OSError as e:return dict(**presentation,opened=False,status='interop_failed',reason=str(e))


def toolchain():
    result=dict(created_utc=core.now(),tools={},models={},pexels=dict(configured=bool(os.environ.get('PEXELS_API_KEY')),masked='••••••' if os.environ.get('PEXELS_API_KEY') else ''),platform=dict(system=platform.system(),release=platform.release(),distro=os.environ.get('WSL_DISTRO_NAME'),windows_browser='not_verified'))
    for name in ('ffmpeg','ffprobe'):
        try:
            path=Path(core.tool(name));proc=subprocess.run([str(path),'-version'],capture_output=True,text=True,timeout=10)
            result['tools'][name]=dict(path=str(path),exists=path.is_file(),executable=os.access(path,os.X_OK),status='passed' if proc.returncode==0 else 'failed',version=proc.stdout.splitlines()[0] if proc.stdout else '',returncode=proc.returncode)
        except (ValueError,OSError,subprocess.TimeoutExpired) as e:result['tools'][name]=dict(status='unavailable',error=str(e))
    for name,folder,package in [('piper','.venv','piper-tts'),('alignment','.venv-align','transformers')]:
        python=core.ROOT/folder/'bin/python';entry=dict(path=str(python),exists=python.is_file(),executable=os.access(python,os.X_OK),status='unavailable')
        if entry['executable']:
            script='import importlib.metadata,json; print(json.dumps({"version":importlib.metadata.version('+repr(package)+')}))'
            try:
                proc=subprocess.run([str(python),'-I','-c',script],capture_output=True,text=True,timeout=20)
                entry.update(status='passed' if proc.returncode==0 else 'failed',returncode=proc.returncode)
                if proc.returncode==0:entry.update(json.loads(proc.stdout))
                else:entry['error']=proc.stderr[-1000:]
            except (OSError,subprocess.TimeoutExpired,ValueError) as e:entry['error']=str(e)
        result['tools'][name]=entry
    for name,folder in [('piper','models/piper'),('alignment','models/alignment/romanian-wav2vec2')]:
        lock=core.ROOT/folder/'model.lock.json'
        try:
            document=core.read(lock);result['models'][name]=dict(path=str(lock),status='manifest_present',sha256=core.sha(lock),revision=document.get('revision'),weights_validation='not_rehashed_in_toolchain_probe')
        except (OSError,ValueError) as e:result['models'][name]=dict(path=str(lock),status='unavailable',error=str(e))
    result['technical_status']='passed' if all(v['status']=='passed' for v in result['tools'].values()) else 'partial'
    return security.public(result)
