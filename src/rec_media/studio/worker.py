"""Separate process with the correct interpreter; never invokes a CLI wrapper."""
from pathlib import Path
import logging
import os
import sys
import time
import threading
import traceback
from .. import core
from .operations import run_request
from .jobs import update_job
from .security import public
from .progress import instrument


class RedactedStream:
    def __init__(self,stream,secret):self.stream=stream;self.secret=secret
    def write(self,text):return self.stream.write(text.replace(self.secret,'[REDACTED]'))
    def __getattr__(self,name):return getattr(self.stream,name)


def main(folder):
    secret=os.environ.get('PEXELS_API_KEY')
    if secret:
        sys.stdout=RedactedStream(sys.stdout,secret);sys.stderr=RedactedStream(sys.stderr,secret)
    folder=Path(folder);job_path=folder/'job.json'
    # Parent publishes PID identity before worker writes final state.
    for _ in range(100):
        job=core.read(job_path)
        if job['status']!='queued':break
        time.sleep(.02)
    request=core.read(folder/'request.json');status='failed';code=1
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    runs=core.ROOT/'work/media/runs';known=set();observer=None
    stop=threading.Event()
    def observe():
        if request['engine']!='media' or request['command']!=['render']:return
        explicit=request['values'].get('resume_run')
        if explicit:core.write(folder/'active-run.json',dict(run_id=explicit));return
        while not stop.wait(.1):
            for state_path in runs.glob('*/run.json'):
                if state_path.parent.name in known:continue
                try:
                    state=core.read(state_path)
                    if state.get('plan',{}).get('material')==request['values']['material']:
                        core.write(folder/'active-run.json',dict(run_id=state_path.parent.name));return
                except (OSError,ValueError):continue
    def on_locked():
        nonlocal observer
        known.update(p.name for p in runs.iterdir()) if runs.exists() else None
        observer=threading.Thread(target=observe,daemon=True);observer.start()
    print(core.now(),'SERVICE',request['engine'],request['command'],flush=True)
    try:
        with instrument(folder):result=public(run_request(request,on_locked=on_locked))
        core.write(folder/'result.json',result)
        if isinstance(result,dict) and result.get('run_id'):core.write(folder/'active-run.json',dict(run_id=result['run_id']))
        status='failed' if isinstance(result,dict) and result.get('technical_status') in ('failed','blocked') else 'complete';code=0 if status=='complete' else 1
    except KeyboardInterrupt:
        status='cancelled';code=130
        print('Întrerupt. Checkpointurile și temporarele rămân păstrate.',file=sys.stderr)
    except Exception as e:
        print('Eroare serviciu:',str(e),file=sys.stderr);traceback.print_exc()
    finally:
        stop.set()
        if observer:observer.join(timeout=.3)
        def finished(job):
            nonlocal status,code
            if job['status']=='cancelling' and status!='complete':status='cancelled';code=130
            return dict(status=status,finished=core.now(),service_returncode=code,current_step=status)
        update_job(folder,finished)
    return code

if __name__=='__main__':raise SystemExit(main(sys.argv[1]))
