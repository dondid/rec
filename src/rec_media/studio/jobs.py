"""Persistent serial queue. Workers invoke Python services in their own sessions."""
from pathlib import Path
import os
import fcntl
import signal
import subprocess
import sys
import threading
import time
import uuid
from .. import core
from . import operations, security


def process_identity(pid):
    try:return Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19]
    except (OSError,IndexError):return None


def alive(job):
    return bool(job.get('pid') and job.get('process_identity') and process_identity(job['pid'])==job['process_identity'])


def update_job(folder, change):
    """Cross-process read/modify/write; atomic rename alone cannot prevent lost updates."""
    folder=Path(folder)
    with (folder/'state.lock').open('a') as guard:
        fcntl.flock(guard,fcntl.LOCK_EX)
        current=core.read(folder/'job.json')
        current.update(change(current) if callable(change) else change)
        core.write(folder/'job.json',current)
        return current


class Queue:
    def __init__(self):
        self.root=core.ROOT/'work/studio/jobs';self.root.mkdir(parents=True,exist_ok=True)
        self.mutex=threading.RLock();self.stop=threading.Event();self.active=None
        self.thread=threading.Thread(target=self.loop,daemon=True);self.thread.start()

    def listing(self):
        rows=[]
        for p in self.root.glob('*/job.json'):
            try:
                j=core.read(p)
                if j['status'] in ('running','cancelling') and not alive(j):
                    result=p.parent/'result.json'
                    if result.exists():
                        r=core.read(result);j.update(status='failed' if r.get('technical_status') in ('failed','blocked') else 'complete',finished=core.now())
                    else:j.update(status='interrupted',diagnostic='Worker absent; inspectează receipts/log. Cauza nu este dedusă din state=running.')
                    def recovered(current):
                        return {k:v for k,v in j.items() if k in ('status','finished','diagnostic')} if current['status'] in ('running','cancelling') else {}
                    j=update_job(p.parent,recovered)
                rows.append(j)
            except (ValueError,OSError):continue
        return sorted(rows,key=lambda x:x['created'],reverse=True)

    def get(self,jid):
        if not isinstance(jid,str) or len(jid)!=32 or any(c not in '0123456789abcdef' for c in jid):raise ValueError('Job ID invalid.')
        return core.read(self.root/jid/'job.json')

    def submit(self,request):
        with self.mutex:
            jid=uuid.uuid4().hex;folder=self.root/jid;folder.mkdir()
            request=operations.prepare_request(request,folder)
            core.write(folder/'request.json',request)
            j=dict(id=jid,type=request['engine']+':'+':'.join(request['command']),status='queued',created=core.now(),started=None,finished=None,
                   material=request['values'].get('material'),progress=None,current_step='În coadă',elapsed=0,request=request,log=str(folder/'worker.log'))
            core.write(folder/'job.json',j)
            return j

    def loop(self):
        while not self.stop.wait(.4):
            with self.mutex:
                rows=self.listing()
                if any(j['status'] in ('running','cancelling') and alive(j) for j in rows):continue
                pending=sorted((j for j in rows if j['status']=='queued'),key=lambda x:x['created'])
                if not pending:continue
                j=pending[0];folder=self.root/j['id'];engine=j['request']['engine']
                python=core.ROOT/'.venv/bin/python' if engine=='tts' else Path(sys.executable)
                env={**os.environ,'PYTHONPATH':str(core.ROOT/'src'),'PYTHONDONTWRITEBYTECODE':'1','PYTHONUNBUFFERED':'1'}
                with (folder/'worker.log').open('ab') as log:
                    try:
                        p=subprocess.Popen([str(python),'-m','rec_media.studio.worker',str(folder)],cwd=core.ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                    except OSError as e:
                        j.update(status='failed',diagnostic=str(e));core.write(folder/'job.json',j);continue
                j.update(status='running',started=core.now(),pid=p.pid,process_identity=process_identity(p.pid),current_step='Serviciu Python în execuție')
                update_job(folder,{k:j[k] for k in ('status','started','pid','process_identity','current_step')})
                threading.Thread(target=self.monitor,args=(p,folder),daemon=True).start()

    def monitor(self,p,folder):
        rc=p.wait()
        def finished(j):
            fields=dict(worker_returncode=rc)
            if j['status'] in ('running','cancelling'):
                fields.update(status='cancelled' if j['status']=='cancelling' else 'interrupted',diagnostic='Worker încheiat fără rezultat; inspectează log/receipts.')
            return fields
        update_job(folder,finished)

    def cancel(self,jid):
        with self.mutex:
            j=self.get(jid);folder=self.root/jid
            if j['status']=='queued':return update_job(folder,dict(status='cancelled',finished=core.now()))
            if j['status'] in ('running','cancelling') and alive(j):
                current=update_job(folder,lambda state:dict(status='cancelling') if state['status'] in ('running','cancelling') else {})
                if current['status']=='cancelling':
                    try:os.killpg(j['pid'],signal.SIGINT)
                    except ProcessLookupError:pass
                return self.get(jid)
            raise ValueError('Jobul nu mai este activ.')

    def resume(self,jid):
        with self.mutex:
            j=self.get(jid)
            if j['status'] not in ('interrupted','failed','cancelled'):raise ValueError('Resume numai după întrerupere/eșec.')
            request=j['request'];request=dict(engine=request['engine'],command=request['command'],values=dict(request['values']))
            if request['command']==['render']:
                active=self.root/jid/'active-run.json'
                if active.exists():request['values']['resume_run']=core.read(active)['run_id']
            new=self.submit(request)
            return update_job(self.root/new['id'],dict(resumed_from=jid))

    def detail(self,jid):
        j=self.get(jid);folder=self.root/jid
        j['log_tail']=(folder/'worker.log').read_text(errors='replace')[-60000:] if (folder/'worker.log').exists() else ''
        if (folder/'result.json').exists():j['result']=core.read(folder/'result.json')
        if j.get('started'):
            from datetime import datetime
            j['elapsed']=round((datetime.fromisoformat(j.get('finished') or core.now())-datetime.fromisoformat(j['started'])).total_seconds(),1)
        if j['request']['command']==['render']:
            active=folder/'active-run.json'
            if active.exists():
                rid=core.read(active)['run_id'];p=core.ROOT/'work/media/runs'/rid/'run.json'
                state=core.read(p);n=state['plan']['scene_count']*len(state['plan']['profiles'])
                completed=len(state.get('rendered_scenes',[]))+len(state.get('reused_scenes',[]))
                j.update(run_id=rid,current_step=f'Scene {completed} / {n}; {state.get("phase")}',progress=dict(completed=completed,total=n,percent=round(100*completed/n) if n else None,scope='scene checkpoints; asamblarea finală separată'))
                if state.get('reused_compositions'):
                    total=len(state['plan']['profiles']);count=len(state.get('completed',[]))
                    j.update(current_step=f'Remux / compoziții reutilizate {count} / {total}',progress=dict(completed=count,total=total,percent=round(100*count/total),scope='compoziții video reutilizate, fără scene regenerate'))
                elif state.get('phase')=='complete' and not completed:
                    j.update(current_step='Export existent verificat',progress=dict(completed=1,total=1,percent=100,scope='export verificat; fără scene regenerate în acest run'))
        from .progress import detail as ffmpeg_detail
        j['ffmpeg']=ffmpeg_detail(folder)
        if j.get('run_id'):
            state=core.read(core.ROOT/'work/media/runs'/j['run_id']/'run.json')
            j['scene_counts']=dict(rendered=len(state.get('rendered_scenes',[])),reused=len(state.get('reused_scenes',[])),invalidated=len(state.get('invalidated_scenes',[])))
        if j['ffmpeg'] and j['ffmpeg'].get('stderr_path'):
            try:
                path=security.path(j['ffmpeg']['stderr_path'],exists=True)
                with path.open('rb') as f:
                    f.seek(max(0,path.stat().st_size-12000));j['ffmpeg_stderr_tail']=f.read().decode(errors='replace')
            except (ValueError,OSError):pass
        return security.public(j)
