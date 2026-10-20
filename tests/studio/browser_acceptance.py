"""Existing Chromium acceptance against an isolated copy, never real review apply."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import urlopen,Request
from urllib.error import HTTPError
from playwright.sync_api import sync_playwright


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--project',type=Path,required=True);ap.add_argument('--report',type=Path,required=True);ap.add_argument('--offline-namespace',action='store_true');ap.add_argument('--recovery-only',action='store_true');args=ap.parse_args()
    project=args.project.resolve();report=args.report.resolve();report.mkdir(parents=True,exist_ok=True)
    if 'work/studio/acceptance/' not in str(project):raise RuntimeError('Acceptance must run in an explicitly isolated project.')
    if args.recovery_only:
        from recovery_acceptance import run
        return run(project,report,args.offline_namespace)
    if args.offline_namespace:subprocess.run(['/usr/sbin/ip','link','set','lo','up'],check=True)
    port=8766;base=f'http://127.0.0.1:{port}'
    out=(report/'server.stdout').open('ab');err=(report/'server.stderr').open('ab')
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}
    server=subprocess.Popen([str(project/'media'),'gui','--no-browser','--port',str(port)],cwd=project,env=env,stdout=out,stderr=err)
    def http(path,body=None,token=None,headers=None):
        h={'Content-Type':'application/json',**(headers or {})}
        if token:h['X-REC-CSRF']=token
        return json.load(urlopen(Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers=h),timeout=30))
    try:
        for _ in range(100):
            try:boot=http('/api/bootstrap');break
            except Exception:time.sleep(.1)
        else:raise RuntimeError('Server did not start.')
        csrf=boot['csrf'];checks=[];errors=[];external=[];page=None
        def post(path,body):return http(path,body,csrf)
        def wait_job(jid):
            deadline=time.monotonic()+180
            while time.monotonic()<deadline:
                j=http('/api/job?id='+jid)
                if j['status'] not in ('queued','running','cancelling'):return j
                page.wait_for_timeout(250) if page is not None and not page.is_closed() else time.sleep(.25)
            raise RuntimeError('Job timeout '+jid)
        last_seen=boot['jobs'][0]['id'] if boot['jobs'] else None
        def latest():
            nonlocal last_seen
            for _ in range(100):
                rows=http('/api/jobs')
                if rows and rows[0]['id']!=last_seen:
                    last_seen=rows[0]['id'];return rows[0]
                page.wait_for_timeout(150)
            raise RuntimeError('No new job: '+page.locator('#notice').inner_text())
        def completed():
            j=wait_job(latest()['id'])
            if j['status']!='complete':raise RuntimeError(json.dumps(j,ensure_ascii=False))
            page.evaluate('refreshMaterial()')
            return j
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
            context=browser.new_context(viewport={'width':1440,'height':1000})
            def route(r):
                if r.request.url.startswith(base) or r.request.url.startswith(('data:','blob:')):r.continue_()
                else:external.append(r.request.url);r.abort()
            context.route('**/*',route)
            page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('dialog',lambda d:d.accept())
            page.goto(base);page.wait_for_selector('h1');assert page.locator('h1').inner_text()=='Production Studio';checks.append('Dashboard')
            def nav(name):
                page.get_by_role('button',name=name,exact=True).first.click()
                page.wait_for_function("name=>document.querySelector('h1')?.textContent===name",arg={'Scenes':'Scene Editor','CTC Review':'CTC Human Review','Assets':'Assets · Alternatives','Library':'Local Asset Library','Settings':'Settings / Hardware','Review':'Human Review Status','Split / Merge':'Split / Merge / Compilation','Jobs':'Jobs / Recovery','Workflow':'Workflow / Batch'}.get(name,name))
            # Explicit material selection; full material is inspected only.
            page.select_option('#material','assets-integral-20261018');page.wait_for_function("() => state.material?.id==='assets-integral-20261018'")
            nav('Materials');assert page.get_by_text('Timeline / metadata',exact=True).count();checks.append('Materials + full material read-only')
            nav('Scenes');page.wait_for_selector('#sceneprops');assert page.locator('.sceneitem').count()==19;checks.append('Full scenes read-only')
            page.select_option('#material','studio-sample');page.wait_for_function("() => state.material?.id==='studio-sample'");page.wait_for_function("() => document.querySelectorAll('.sceneitem').length===3")
            nav('Scenes');page.screenshot(path=str(report/'scenes-before.png'),full_page=True)
            # Select alternative in isolated library; then use backend undo.
            page.locator('[data-candidate="4"]').first.click();page.wait_for_timeout(250);changed=completed();checks.append('Asset selection')
            nav('Materials');nav('Scenes');page.locator('#undo').click();page.wait_for_timeout(200);completed();checks.append('Asset undo')
            nav('CTC Review');page.wait_for_selector('[data-decision="ACCEPT"]');page.locator('[name=reviewer]').fill('browser fixture only');page.locator('[data-decision="NEEDS_REVIEW"]').click()
            page.locator('#ctc-validate').click();page.wait_for_timeout(200);completed();checks.append('CTC explicit decisions validation, no apply')
            nav('Subtitles');page.locator('[name=preset]').select_option('boxed');page.get_by_text('Stil complet / font / profile overrides (JSON)',exact=True).click();page.locator('#subtitlejson').fill(json.dumps({'profiles':{'custom':{'font_size':24,'line_spacing':2,'margin_v':.08}}}));page.get_by_role('button',name='Save subtitle style',exact=True).click();page.wait_for_timeout(300);checks.append('Subtitle settings')
            page.locator('[name=mode]').select_option('highlight');page.locator('#subtitlepreview').click();page.wait_for_selector('#subtitlepreviewresult img',timeout=90000);checks.append('Subtitle real ASS raster preview')
            page.screenshot(path=str(report/'subtitles.png'),full_page=True)
            nav('Audio Mix');page.locator('#addtrack').click();page.locator('.track [name=path]').fill('input/technical-music.wav');page.locator('.track [name=volume_db]').fill('-24');page.locator('.track [name=loop]').check();page.locator('.track [name=creator]').fill('local generated fixture');page.locator('.track [name=license]').fill('technical fixture only');page.locator('[name=enabled]').check();page.get_by_role('button',name='Save configuration',exact=True).click();page.wait_for_timeout(300);completed();checks.append('Audio Mix config')
            nav('Render');page.locator('[name=landscape]').uncheck();page.locator('[name=custom]').check();page.locator('[name=width]').fill('640');page.locator('[name=height]').fill('360');page.locator('#renderplan').click();page.wait_for_selector('#renderplanresult pre');checks.append('Render preflight')
            page.get_by_role('button',name='START RENDER',exact=True).click();page.wait_for_timeout(300);jid=latest()['id'];nav('Jobs');page.locator(f'[data-inspect="{jid}"]').click();page.wait_for_timeout(500);page.screenshot(path=str(report/'jobs-running.png'),full_page=True)
            job=wait_job(jid);assert job['status']=='complete',job;checks.append('Render sample + progress/logs')
            nav('Verify');page.locator('#verify-material').click();page.wait_for_timeout(300);completed();checks.append('Verify material/provenance')
            output=job['result']['outputs'][0]['path'];v=post('/api/jobs',dict(engine='media',command=['verify'],values={'video':output}));assert wait_job(v['id'])['status']=='complete';checks.append('Verify rendered sample video')
            nav('Outputs');assert page.locator('[data-output]').count();page.locator('[data-output]').first.click();page.wait_for_timeout(300);page.screenshot(path=str(report/'outputs.png'),full_page=True);checks.append('Outputs preview')
            nav('Settings');assert page.get_by_text('CPU / RAM / GPU',exact=True).count();checks.append('Settings / hardware')
            nav('Logs');page.wait_for_selector('#joblist table');checks.append('Logs')
            # All remaining primary pages load without exceptions.
            for name in ['Text / TTS','Split Text','Alignment','Assets','Library','Titles / Thumbnail','Split / Merge','Workflow','Review']:
                nav(name);checks.append(name)
            browser.close();browser_version=browser.version
        # Exercise the shared legacy orchestrators without synthesis or inference.
        (project/'input/studio-workflow-fixture.txt').write_text('Text sintetic pentru pregătire locală. Fără sinteză audio.\n')
        if not (project/'pronunciations.json').exists():(project/'pronunciations.json').write_text('[]\n')
        destination=project/'output'/('workflow-prepare-'+str(time.time_ns()))
        plan=dict(steps=[dict(id='inspect',tool='media',args=['scenes','studio-sample','--inspect'],inputs=[],outputs=[]),
              dict(id='prepare',tool='tts',args=['prepare',str(project/'input/studio-workflow-fixture.txt'),'--output-dir',str(destination)],inputs=[str(project/'input/studio-workflow-fixture.txt')],outputs=[str(destination)])])
        workflow_job=post('/api/jobs',dict(engine='media',command=['workflow'],values={},inline={'plan':plan}))
        workflow_result=wait_job(workflow_job['id']);assert workflow_result['status']=='complete',workflow_result
        assert workflow_result['result']['workflow_status']=='complete';checks.append('Workflow media + TTS prepare via shared orchestrator')
        batch_file=project/'input/studio-batch-fixture.json'
        batch_file.write_text(json.dumps(dict(jobs=[dict(args=['thumbnail','studio-sample','--text','Studio fixture','--profiles','landscape','--output-dir',str(project/'output'/('batch-thumbnail-'+str(time.time_ns())))])])))
        batch_job=post('/api/jobs',dict(engine='media',command=['batch'],values={'file':str(batch_file)}));batch_result=wait_job(batch_job['id']);assert batch_result['status']=='complete',batch_result;checks.append('Batch thumbnail via shared service')
        # Negative API boundaries are real HTTP calls.
        negatives=[('/api/jobs',dict(engine='media',command=['scenes'],values={'material':'../bad'}),csrf,{}),('/api/jobs',dict(engine='media',command=['scenes'],values={'material':'studio-sample'}),None,{}),('/api/jobs',dict(engine='media',command=['scenes'],values={'material':'studio-sample'}),csrf,{'Origin':'https://evil.invalid'})]
        for path,body,token,h in negatives:
            try:http(path,body,token,h);raise AssertionError('Unsafe API request accepted')
            except HTTPError as e:assert e.code==400
        for path in ['/files?path=/etc/passwd','/files?path=.git/config','/api/files?path=../']:
            try:http(path);raise AssertionError('Path escape accepted')
            except HTTPError as e:assert e.code==400
        checks.append('HTTP CSRF / origin / path protection')
        # A queued job is cancelable. Restart preserves all successful receipts.
        a=post('/api/jobs',dict(engine='media',command=['render'],values={'material':'studio-sample','profiles':'custom','width':640,'height':360,'subtitles':'highlight','output_root':'output/cancel-fixture-'+str(time.time_ns())}))
        post('/api/cancel',{'id':a['id']});cancelled=wait_job(a['id']);assert cancelled['status']=='cancelled';checks.append('Cancel queued job')
        before=[j['id'] for j in http('/api/jobs') if j['status']=='complete']
        server.terminate();server.wait(timeout=10)
        server=subprocess.Popen([str(project/'media'),'gui','--no-browser','--port',str(port)],cwd=project,env=env,stdout=out,stderr=err)
        for _ in range(100):
            try:boot=http('/api/bootstrap');break
            except Exception:time.sleep(.1)
        assert set(before)<={j['id'] for j in boot['jobs'] if j['status']=='complete'};checks.append('Restart successful jobs preserved')
        # Resume makes a new receipt, keeping the original cancelled attempt.
        csrf=boot['csrf'];resumed=http('/api/resume',{'id':a['id']},csrf);r=wait_job(resumed['id']);assert r['status']=='complete',r;checks.append('Resume cancelled fixture render')
        assert not errors,errors
        assert not external,external
        from datetime import datetime,timezone
        result=dict(utc=datetime.now(timezone.utc).isoformat(),version='1.0.0',browser=browser_version,checks=checks,js_errors=errors,external_requests=external,offline_namespace=args.offline_namespace,sample_render=job,technical_status='passed',browser_review='passed',visual_sample_review='not_reviewed',listening_review='not_listened',editorial_review='not_reviewed',ctc_human_review='pending')
        (report/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(checks=checks,browser=browser_version,js_errors=errors,external_requests=external),ensure_ascii=False))
    finally:
        if server.poll() is None:server.terminate();server.wait(timeout=10)
        out.close();err.close()

if __name__=='__main__':main()
