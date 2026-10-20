"""HTTP active-cancel/resume/restart and exact checkpoint evidence on a sample."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import time
from urllib.request import Request,urlopen


def run(project,report,offline_namespace,browser_review=False):
    project=project.resolve();report.mkdir(parents=True,exist_ok=True)
    if offline_namespace:subprocess.run(['/usr/sbin/ip','link','set','lo','up'],check=True)
    log=(report/'server.log').open('ab');port=8767;base=f'http://127.0.0.1:{port}'
    def start():return subprocess.Popen([str(project/'media'),'gui','--port',str(port),'--no-browser'],cwd=project,stdout=log,stderr=log)
    server=start();token='';pw=None;browser=None;page=None;browser_checks=[]
    if browser_review:
        from playwright.sync_api import sync_playwright
        pw=sync_playwright().start();browser=pw.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage']);page=browser.new_page(viewport={'width':1500,'height':1000});page.on('dialog',lambda d:d.accept())
    def http(path,body=None):
        headers={'Content-Type':'application/json','X-REC-CSRF':token}
        return json.load(urlopen(Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers=headers),timeout=30))
    def boot():
        nonlocal token
        for _ in range(100):
            try:token=http('/api/bootstrap')['csrf'];return
            except Exception:time.sleep(.1)
        raise RuntimeError('Server not available.')
    try:
        boot()
        disabled=http('/api/jobs',dict(engine='media',command=['audio-mix'],values=dict(material='studio-sample',disable=True)))
        for _ in range(100):
            d=http('/api/job?id='+disabled['id'])
            if d['status'] not in ('queued','running'):break
            time.sleep(.1)
        assert d['status']=='complete'
        output='output/active-cancel-'+str(time.time_ns())
        request=dict(engine='media',command=['render'],values=dict(material='studio-sample',profiles='custom',width=960,height=540,subtitles='off' if browser_review else 'scroll',title='Recovery fixture '+str(time.time_ns()),output_root=output))
        job=http('/api/jobs',request);jid=job['id'];deadline=time.monotonic()+90
        while time.monotonic()<deadline:
            active=http('/api/job?id='+jid)
            if active['status']=='running' and active.get('started') and (active.get('progress') or {}).get('completed',0)>=1:break
            if active['status'] not in ('queued','running'):raise RuntimeError(str(active))
            time.sleep(.15)
        else:raise RuntimeError('No checkpoint reached.')
        run_id=active['run_id'];folder=project/'work/media/runs'/run_id
        checkpoints={str(p.relative_to(project)):dict(sha256=hashlib.file_digest(p.open('rb'),'sha256').hexdigest(),mtime_ns=p.stat().st_mtime_ns) for p in folder.rglob('scene-*.mkv') if p.with_suffix('.receipt.json').exists()}
        assert checkpoints
        if page:
            page.goto(base);page.wait_for_function('()=>!studioUI.busy');page.get_by_role('button',name='Jobs',exact=True).click();page.wait_for_function('()=>!studioUI.busy');page.locator('[data-inspect="'+jid+'"]').click();page.wait_for_selector('#live-frame-progress');assert jid[:8] in page.locator('#jobbar').inner_text();page.wait_for_function("()=>document.querySelector('#logtext').textContent.includes('FFmpeg')");page.screenshot(path=str(report/'live-progress.png'),full_page=True);browser_checks.append(dict(stage='active',frame=page.locator('#live-frame-progress').inner_text(),scenes=page.locator('#live-scene-counts').inner_text(),run_id=active['run_id']));page.locator('#canceljob').click()
        else:http('/api/cancel',{'id':jid})
        for _ in range(100):
            cancelled=http('/api/job?id='+jid)
            if cancelled['status'] not in ('running','cancelling'):break
            time.sleep(.1)
        assert cancelled['status']=='cancelled',cancelled
        assert not list((project/output).rglob('video.mp4'))
        if page:
            page.wait_for_selector('#resumejob',state='visible');page.locator('#resumejob').click();page.wait_for_function('(old)=>state.job!==old',arg=jid);rid=page.evaluate('()=>state.job');browser_checks.append('Cancel and Resume buttons')
        else:
            resumed=http('/api/resume',{'id':jid});rid=resumed['id']
        for _ in range(100):
            second=http('/api/job?id='+rid)
            if second['status']=='running':break
            time.sleep(.1)
        server.terminate();server.wait(timeout=10)
        server=start();boot()
        recovered=http('/api/job?id='+rid)
        assert recovered['id']==rid
        deadline=time.monotonic()+180
        while time.monotonic()<deadline:
            finished=http('/api/job?id='+rid)
            if finished['status'] not in ('queued','running','cancelling'):break
            time.sleep(.3)
        assert finished['status']=='complete',finished
        if page:
            page.reload();page.wait_for_function('()=>!studioUI.busy');page.get_by_role('button',name='Jobs',exact=True).click();page.wait_for_function('()=>!studioUI.busy');page.locator('[data-inspect="'+rid+'"]').click();page.wait_for_function("()=>document.querySelector('#live-job-heading')?.textContent.includes('complete')");page.screenshot(path=str(report/'resumed-progress.png'),full_page=True);browser_checks.append(dict(stage='resumed',scenes=page.locator('#live-scene-counts').inner_text(),frame=page.locator('#live-frame-progress').inner_text()));assert finished.get('scene_counts',{}).get('reused',0)>=1
        for relative,meta in checkpoints.items():
            p=project/relative
            assert hashlib.file_digest(p.open('rb'),'sha256').hexdigest()==meta['sha256'] and p.stat().st_mtime_ns==meta['mtime_ns']
        assert http('/api/job?id='+jid)['status']=='cancelled'
        video=finished['result']['outputs'][0]['path']
        req=Request(base+'/files?path='+video,headers={'Range':'bytes=0-99'})
        with urlopen(req) as r:assert r.status==206 and len(r.read())==100
        from datetime import datetime,timezone
        result=dict(utc=datetime.now(timezone.utc).isoformat(),technical_status='passed',offline_namespace=offline_namespace,active_cancel=cancelled,resumed=finished,
                    browser_checks=browser_checks,first_attempt_preserved=True,checkpoint_hash_mtime_unchanged=checkpoints,range_playback='passed',restart_active_job_preserved=True,listening_review='not_listened',ctc_human_review='pending')
        (report/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print('PASSED active cancel, no publication, resume, active-server restart, exact checkpoint reuse, byte ranges')
    finally:
        if browser:browser.close()
        if pw:pw.stop()
        if server.poll() is None:server.terminate();server.wait(timeout=10)
        log.close()
