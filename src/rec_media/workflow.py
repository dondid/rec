"""Explicit, resumable subprocess orchestration over the public media/tts CLIs."""
import contextlib
import fcntl
from pathlib import Path
import re
import subprocess
import uuid

from .core import ROOT, key, now, read, sha, write


def artifacts(paths,base):
    result={}
    for name in paths:
        path=Path(name);path=path if path.is_absolute() else base/path
        if path.is_dir():
            files=sorted(p for p in path.rglob('*') if p.is_file())
            if not files:raise ValueError(f'Director artefact gol: {path}')
        else:files=[path]
        for file in files:result[str(file.resolve())]=sha(file)
    return result


def run(plan_path,only=None,disable=None,rerun=None):
    plan_path=Path(plan_path).resolve();plan=read(plan_path);base=plan_path.parent
    steps=plan['steps'];ids=[s['id'] for s in steps]
    if not ids or len(ids)!=len(set(ids)) or any(not re.fullmatch('[A-Za-z0-9_-]{1,80}',i) for i in ids):raise ValueError('ID-uri de etape invalide/repetate.')
    only=set(only or []);disable=set(disable or []);rerun=set(rerun or [])
    if (only|disable|rerun)-set(ids):raise ValueError('Etapă necunoscută.')
    previous=set()
    from .cli import parser
    for step in steps:
        if step.get('tool') not in ('tts','media') or not isinstance(step.get('args'),list) or not step['args'] or any(not isinstance(a,str) for a in step['args']):raise ValueError('Etapa cere tool tts/media și args ca listă de șiruri.')
        if not set(step.get('depends_on',[]))<=previous:raise ValueError('Dependențele trebuie declarate înaintea etapei.')
        if step['tool']=='media':
            child=parser().parse_args(step['args'])
            if child.command in ('workflow','batch'):raise ValueError('Orchestrare recursivă refuzată.')
        elif step['args'][0] not in ('render','preview','prepare','verify','doctor'):raise ValueError('Workflow TTS permite numai procesare locală, fără instalări.')
        if not isinstance(step.get('inputs',[]),list) or not isinstance(step.get('outputs',[]),list):raise ValueError('inputs/outputs trebuie să fie liste de căi.')
        previous.add(step['id'])
    folder=base/(plan_path.stem+'.state');folder.mkdir(exist_ok=True)
    with (folder/'workflow.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('Workflow deja în execuție.')
        state_path=folder/'state.json';old=read(state_path) if state_path.exists() else {'steps':{}}
        records=dict(old['steps']);executed=[];satisfied=set()
        implementations={str(p.relative_to(ROOT)):sha(p) for package in ['rec_media','rec_tts'] for p in (ROOT/'src'/package).glob('*.py')}
        for step in steps:
            identifier=step['id']
            if not step.get('enabled',True) or identifier in disable:
                executed.append(dict(id=identifier,status='disabled'));continue
            if only and identifier not in only:
                executed.append(dict(id=identifier,status='not_selected'));continue
            try:
                missing=set(step.get('depends_on',[]))-satisfied
                # Independent reruns can consume previous verified dependency artifacts.
                for dependency in list(missing):
                    prior=records.get(dependency,{})
                    if prior.get('status')=='passed' and prior.get('artifacts') and all(Path(p).is_file() and sha(p)==h for p,h in prior['artifacts'].items()):missing.remove(dependency)
                if missing:raise ValueError('Dependențe incomplete: '+', '.join(sorted(missing)))
                inputs=artifacts(step.get('inputs',[]),base)
                signature=key(dict(step=step,inputs=inputs,dependencies={dep:records[dep].get('signature') for dep in step.get('depends_on',[])},implementation=implementations))
                prior=records.get(identifier,{})
                if identifier not in rerun and prior.get('signature')==signature and prior.get('status')=='passed' and prior.get('artifacts') and all(Path(p).is_file() and sha(p)==h for p,h in prior['artifacts'].items()):
                    executed.append(dict(id=identifier,status='passed',resumed=True));satisfied.add(identifier);continue
                attempt=folder/(identifier+'-'+uuid.uuid4().hex)
                args=[str(ROOT/step['tool'])]
                if step['tool']=='media':args+=['--report',str(attempt.with_suffix('.json'))]
                args+=step['args']
                write(state_path,dict(created_utc=now(),phase='running',active=identifier,steps=records))
                with attempt.with_suffix('.log').open('w') as log:
                    process=subprocess.run(args,cwd=base,stdout=log,stderr=subprocess.STDOUT)
                if process.returncode:raise ValueError(f'Exit {process.returncode}; diagnostic: {attempt.with_suffix(".log")}')
                outputs=artifacts(step.get('outputs',[]),base)
                if step['tool']=='media':
                    receipt=attempt.with_suffix('.json');outputs[str(receipt)]=sha(receipt)
                    result=read(receipt)
                    for item in result.get('outputs',[]):
                        path=Path(item['path'] if isinstance(item,dict) else item)
                        outputs[str(path.resolve())]=sha(path)
                        for sidecar in [path.with_suffix('.json'),path.with_suffix('.report.json')]:
                            if sidecar.is_file():outputs[str(sidecar.resolve())]=sha(sidecar)
                if not outputs:raise ValueError('Etapa TTS cere outputs explicite pentru reluare verificată.')
                records[identifier]=dict(status='passed',signature=signature,artifacts=outputs,created_utc=now(),log=str(attempt.with_suffix('.log')))
                executed.append(dict(id=identifier,status='passed',resumed=False));satisfied.add(identifier)
            except Exception as error:
                previous=records.get(identifier,{})
                failure=dict(status='failed',error=str(error),created_utc=now())
                # A failed retry must not erase the hashes/log of a completed
                # attempt. Retain evidence, without treating it as current success.
                success=previous if previous.get('status')=='passed' else previous.get('previous_success')
                if success:failure['previous_success']=success
                records[identifier]=failure;executed.append(dict(id=identifier,status='failed',error=str(error)))
                write(state_path,dict(created_utc=now(),phase='failed',steps=records))
                return dict(technical_status='failed',steps=executed,state=str(state_path))
            write(state_path,dict(created_utc=now(),phase='running',steps=records))
        incomplete=[s['id'] for s in steps if s.get('enabled',True) and s['id'] not in disable and s['id'] not in satisfied]
        phase='partial' if incomplete else 'complete'
        write(state_path,dict(created_utc=now(),phase=phase,incomplete=incomplete,steps=records))
        return dict(technical_status='passed',workflow_status=phase,incomplete=incomplete,steps=executed,state=str(state_path))


def synthesize_parts(manifest,output,apply=False):
    manifest=Path(manifest).resolve();plan=read(manifest);output=Path(output).resolve();jobs=[]
    for part in plan['parts']:
        text=manifest.parent/part['path']
        if key(text.read_bytes().decode('utf-8'))!=part['text_sha256']:raise ValueError('Partea text s-a schimbat față de plan.')
        jobs.append(dict(text=str(text),audio=str(output/(part['id']+'.mp3'))))
    if not apply:return dict(technical_status='planned',jobs=jobs)
    output.mkdir(parents=True,exist_ok=True)
    results=[]
    for job in jobs:
        process=subprocess.run([str(ROOT/'tts'),'render',job['text'],'-o',job['audio']],capture_output=True,text=True)
        result=dict(job,returncode=process.returncode,stdout=process.stdout,stderr=process.stderr);results.append(result)
        write(output/'synthesis-parts.json',dict(created_utc=now(),jobs=results))
        if process.returncode:return dict(technical_status='failed',jobs=results)
    return dict(technical_status='passed',jobs=results)
