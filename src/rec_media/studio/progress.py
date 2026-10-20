"""Worker-scoped FFmpeg telemetry; no renderer/pixel code or CLI changes."""
from contextlib import contextmanager
from pathlib import Path
import math
import subprocess
import uuid
from .. import core
from . import security


def progress_block(path):
    try:
        with Path(path).open('rb') as f:
            f.seek(max(0,Path(path).stat().st_size-32768));lines=f.read().decode(errors='replace').splitlines()
    except OSError:return {}
    current={};last={}
    for line in lines:
        k,sep,v=line.partition('=')
        if not sep:continue
        current[k]=v
        if k=='progress':last=current;current={}
    return last


def finite_number(value):
    try:
        n=float(value)
        return n if math.isfinite(n) else None
    except (TypeError,ValueError):return None


@contextmanager
def instrument(folder):
    """Only this service process receives -progress. Effective argv is receipted."""
    original=subprocess.Popen;directory=Path(folder)/'ffmpeg';directory.mkdir(exist_ok=True)
    class TrackedPopen(original):
        def __init__(self,args,*pos,**kw):
            self.telemetry=None
            if isinstance(args,(list,tuple)) and args and Path(str(args[0])).name=='ffmpeg':
                if kw.get('shell'):raise ValueError('Shell FFmpeg refuzat.')
                command=[str(a) for a in args];identifier=uuid.uuid4().hex
                progress=directory/(identifier+'.progress');self.telemetry=directory/(identifier+'.json')
                effective=[command[0]];i=1
                while i<len(command):
                    if command[i]=='-stats_period':i+=2;continue
                    effective.append(command[i]);i+=1
                effective[1:1]=['-progress',str(progress),'-stats_period','0.25']
                expected=None
                if '-frames:v' in effective:
                    try:expected=int(effective[effective.index('-frames:v')+1])
                    except (ValueError,IndexError):pass
                stderr=kw.get('stderr');stderr_path=getattr(stderr,'name',None)
                self.receipt=dict(id=identifier,created_utc=core.now(),phase='starting',progress_path=str(progress),expected_frames=expected,
                    effective_argv=effective,original_argv=command,stderr_path=stderr_path if isinstance(stderr_path,str) else None,
                    stage='decode / verify' if '-f' in effective and 'null' in effective else 'encode / scene / mux')
                core.write(self.telemetry,security.public(self.receipt));args=effective
            super().__init__(args,*pos,**kw)
            if self.telemetry:
                self.receipt.update(pid=self.pid,phase='running');self.record()
                print(core.now(),'FFmpeg',self.receipt['stage'],'pid',self.pid,'frames',self.receipt['expected_frames'],flush=True)
        def record(self):
            try:core.write(self.telemetry,security.public(self.receipt))
            except OSError:pass  # Telemetry cannot turn a successful export into a failure.
        def finish(self,code):
            if self.telemetry and self.receipt.get('phase')!='complete':
                self.receipt.update(phase='complete',returncode=code,finished_utc=core.now());self.record()
                print(core.now(),'FFmpeg returncode',code,'pid',self.pid,flush=True)
        def wait(self,*a,**kw):
            code=super().wait(*a,**kw);self.finish(code);return code
        def poll(self):
            code=super().poll()
            if code is not None:self.finish(code)
            return code
    subprocess.Popen=TrackedPopen
    try:yield
    finally:subprocess.Popen=original


def detail(folder):
    records=[]
    for path in (Path(folder)/'ffmpeg').glob('*.json'):
        try:records.append(core.read(path))
        except (OSError,ValueError):continue
    if not records:return None
    active=[r for r in records if r.get('phase')=='running']
    chosen=max(active or records,key=lambda r:r['created_utc']);block=progress_block(chosen['progress_path'])
    frame=finite_number(block.get('frame'));expected=chosen.get('expected_frames');elapsed=finite_number(block.get('out_time_us'))
    return dict(command_id=chosen['id'],pid=chosen.get('pid'),phase=chosen['phase'],stage=chosen['stage'],frame=int(frame) if frame is not None else None,
        expected_frames=expected,percent=min(100,round(frame/expected*100,1)) if frame is not None and expected else None,
        out_time_seconds=elapsed/1_000_000 if elapsed is not None else None,fps=finite_number(block.get('fps')),speed=block.get('speed'),
        progress_status=block.get('progress','waiting'),returncode=chosen.get('returncode'),stderr_path=chosen.get('stderr_path'))
