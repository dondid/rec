"""Real Chromium hardening probe. Private existing audio/CTC are never regenerated."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from playwright.sync_api import sync_playwright


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--project',type=Path,required=True);ap.add_argument('--report',type=Path,required=True);ap.add_argument('--offline-namespace',action='store_true');args=ap.parse_args()
    project=args.project.resolve();report=args.report.resolve();report.mkdir(parents=True,exist_ok=True)
    if 'work/studio/hardening-' not in str(project):raise RuntimeError('Use only an explicitly isolated hardening project.')
    if args.offline_namespace:subprocess.run(['/usr/sbin/ip','link','set','lo','up'],check=True)
    base='http://127.0.0.1:8768';secret='hardening-secret-sentinel';env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PEXELS_API_KEY':secret}
    out=(report/'server.stdout').open('ab');err=(report/'server.stderr').open('ab')
    server=subprocess.Popen([str(project/'media'),'gui','--no-browser','--port','8768'],cwd=project,env=env,stdout=out,stderr=err)
    token='';checks=[];errors=[];external=[];page=None;browser=None;dialog_action='accept'
    def http(path,body=None,headers=None):
        h={'Content-Type':'application/json','X-REC-CSRF':token,**(headers or {})}
        return json.load(urlopen(Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers=h),timeout=30))
    def pause(ms=150):
        if page is not None and not page.is_closed():page.wait_for_timeout(ms)
        else:time.sleep(ms/1000)
    def wait_job(jid):
        deadline=time.monotonic()+120
        while time.monotonic()<deadline:
            j=http('/api/job?id='+jid)
            if j['status'] not in ('queued','running','cancelling'):return j
            pause()
        raise RuntimeError('Job timeout '+jid)
    seen=None
    def latest_done():
        nonlocal seen
        for _ in range(150):
            rows=http('/api/jobs')
            if rows and rows[0]['id']!=seen:
                seen=rows[0]['id'];j=wait_job(seen)
                if j['status']!='complete':raise RuntimeError(json.dumps(j,ensure_ascii=False))
                return j
            pause()
        raise RuntimeError('No new job: '+page.locator('#notice').inner_text())
    try:
        for _ in range(100):
            try:boot=http('/api/bootstrap');token=boot['csrf'];break
            except Exception:time.sleep(.1)
        else:raise RuntimeError('Server not available.')
        seen=boot['jobs'][0]['id'] if boot['jobs'] else None
        before_full=(project/'materials/assets-integral-20261018/material.json').read_bytes()
        before_sample=(project/'materials/studio-sample/material.json').read_bytes()
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
            context=browser.new_context(viewport={'width':1500,'height':1000},permissions=['clipboard-read','clipboard-write'])
            def route(r):
                if r.request.url.startswith(base) or r.request.url.startswith(('data:','blob:')):r.continue_()
                else:external.append(r.request.url);r.abort()
            context.route('**/*',route)
            page=context.new_page();page.set_default_timeout(30000);page.on('pageerror',lambda e:errors.append(str(e)))
            def dialog(d):
                nonlocal dialog_action
                if dialog_action=='dismiss':d.dismiss();dialog_action='accept'
                else:d.accept()
            page.on('dialog',dialog)
            page.goto(base);page.wait_for_selector('h1');page.wait_for_function('()=>!studioUI.busy')
            checks.append('Dashboard loading complete')
            def nav(name):
                page.locator('#nav button').filter(has_text=__import__('re').compile('^'+__import__('re').escape(name)+'$')).click()
                page.wait_for_function('()=>!studioUI.busy');pause(60)
                assert not page.locator('.error-state').count(),page.locator('#page').inner_text()
            def material(mid):
                page.select_option('#material',mid);page.wait_for_function('(mid)=>(mid?state.material?.id===mid:!state.material)&&!studioUI.busy',arg=mid)
            # Full material inspection is strictly read-only, no preview renders of the integral.
            material('assets-integral-20261018');nav('Scenes');assert page.locator('.sceneitem').count()==19;checks.append('Real full material readonly')
            material('crop-fixture');nav('Scenes');page.wait_for_selector('#source-metadata');page.wait_for_function("()=>!document.querySelector('#source-metadata').textContent.includes('verifică')")
            before_crop=(project/'materials/crop-fixture/material.json').read_bytes()
            page.locator('#sceneprops [name=focal_x]').fill('0.15');page.locator('#scene-preview-real').click();first=latest_done();page.wait_for_selector('[data-rendered-profile=portrait] img')
            assert first['result']['outputs'][0]['type']=='image';assert page.evaluate('()=>state.dirty');checks.append('Backend crop preview landscape + portrait, unsaved retained')
            # Pointer drag is tested on the original source, not on a client-side crop renderer.
            image=page.locator('#focalpreview img');rect=image.bounding_box();page.mouse.move(rect['x']+rect['width']*.2,rect['y']+rect['height']*.5);page.mouse.down();page.mouse.move(rect['x']+rect['width']*.85,rect['y']+rect['height']*.5,steps=5);page.mouse.up();dragged=latest_done()
            assert float(page.locator('#sceneprops [name=focal_x]').input_value())>.8;checks.append('Focal drag with production preview')
            page.locator('#scene-preview-real').click();cached=latest_done();assert cached['result']['cache_hit'];checks.append('Preview checksum/decode cache hit')
            assert (project/'materials/crop-fixture/material.json').read_bytes()==before_crop
            dialog_action='dismiss';page.locator('#nav button').filter(has_text=__import__('re').compile('^Outputs$')).click();pause();assert page.evaluate('()=>state.page')=='Scenes';assert page.evaluate('()=>state.dirty');checks.append('Unsaved navigation dismiss preserves controls')
            page.locator('#sceneprops button[type=submit]').click();saved=latest_done();page.wait_for_function("()=>document.querySelector('#scene-save-state')?.textContent.includes('salvată')");checks.append('Save indicator and atomic scene edit')
            page.locator('#scene-undo-top').click();latest_done();page.wait_for_function('()=>!state.dirty');checks.append('Visible Undo')
            page.locator('#scene-next-pending').click();pause();assert page.evaluate('()=>state.scene')==1;checks.append('Next NEEDS_REVIEW')
            page.locator('h1').click();page.keyboard.press('ArrowLeft');page.wait_for_function('()=>state.scene===0');page.locator('#sceneprops [name=focal_x]').focus();page.keyboard.press('ArrowRight');pause();assert page.evaluate('()=>state.scene')==0;page.locator('h1').click();page.keyboard.press('r');page.wait_for_function('()=>state.scene===1');checks.append('Keyboard navigation and input shortcut isolation')
            nav('Review');page.locator('#review-fullscreen').click();page.wait_for_function('()=>Boolean(document.fullscreenElement)');page.locator('#portrait').click();page.wait_for_function("()=>state.profile==='portrait'&&Boolean(document.fullscreenElement)");page.screenshot(path=str(report/'review-fullscreen.png'))
            page.locator('#scene-needs-review').click();latest_done();assert http('/api/material?id=crop-fixture')['editorial_review_status']=='not_reviewed';checks.append('Fullscreen profile toggle + explicit review, global editorial unchanged')
            page.evaluate('()=>document.exitFullscreen()');page.wait_for_function('()=>!document.fullscreenElement');nav('Scenes')
            material('studio-sample');nav('Scenes');page.wait_for_selector('#trim-scrub');page.wait_for_function('()=>!document.querySelector("#trim-scrub").disabled')
            page.locator('#sceneprops [name=scope]').select_option('');page.locator('#sceneprops [name=source_start]').fill('1');page.locator('#sceneprops [name=source_end]').fill('2');page.locator('#sceneprops [name=short_policy]').select_option('freeze')
            scrub=page.locator('#trim-scrub');box=scrub.bounding_box();scrub.click(position={'x':box['width']/2,'y':box['height']/2});trim=latest_done();page.wait_for_selector('[data-rendered-profile=landscape] img')
            assert all(o['metadata']['muted'] and 1<=o['metadata']['requested_frame_time']<=2 for o in trim['result']['outputs']);checks.append('Video trim/scrub real source frame + mute + short policy')
            page.screenshot(path=str(report/'trim.png'),full_page=True)
            page.locator('#sceneprops [name=source_end]').fill('.5');page.locator('#trim-frame').click();page.wait_for_selector('#rendered-previews .error-state');assert 'source_end' in page.locator('#notice').inner_text();checks.append('Invalid trim shows actionable error')
            assert (project/'materials/studio-sample/material.json').read_bytes()==before_sample
            material('crop-fixture');nav('Scenes');page.locator('#scene-next').click();pause();page.locator('#sceneprops [name=transition]').select_option('crossfade');page.locator('#transition-preview').click();transition=latest_done();page.wait_for_selector('#rendered-previews video');page.wait_for_function('()=>document.querySelector("#rendered-previews video").videoWidth>0');checks.append('Real cached crossfade clip')
            page.locator('#transition-preview').click();again=latest_done();assert again['result']['cache_hit'];checks.append('Transition cache reuse')
            nav('Library');page.locator('#library-audio-tab').click();page.wait_for_selector('#audio-library-grid');page.locator('#audio-query').fill('no-such-fixture-987654321');page.locator('#audio-search').click();page.wait_for_selector('#audio-library-grid .empty-state');page.locator('#audio-query').fill('');checks.append('Audio library empty state')
            page.locator('[name=audio_path]').fill('input/technical-music.wav');page.locator('[name=audio_creator]').fill('browser fixture');page.locator('[name=audio_license]').fill('technical fixture only');page.locator('#audio-import').click();audio=latest_done();page.wait_for_selector('.audio-asset audio');assert audio['result']['asset']['sample_rate']==44100 and audio['result']['asset']['channels']==2;checks.append('Audio import/full decode/index/provenance')
            page.locator('[data-use-audio]').first.click();page.wait_for_selector('#audioform');assert page.locator('.track [name=source]').first.input_value().startswith('audio-library:');page.locator('#addtrack').click();assert page.locator('.track [name=source]').first.input_value().startswith('audio-library:');page.locator('[data-trackremove="1"]').click();checks.append('Audio library reuse/provenance survives adding/removing track')
            page.locator('#mixvalidate').click();mix=latest_done();assert mix['result']['audio_mix']['tracks'][0]['source']['creator']=='browser fixture';assert page.evaluate('()=>state.dirty');checks.append('Audio Mix validation preserves unsaved configuration')
            nav('Settings');page.locator('#check-toolchain').click();tools=latest_done();assert tools['result']['tools']['ffmpeg']['status']=='passed';assert tools['result']['pexels']['masked']=='••••••';assert secret not in page.content();page.wait_for_selector('#platform-paths pre');assert 'wsl.localhost' in page.locator('#platform-paths').inner_text() and 'Debian' in page.locator('#platform-paths').inner_text();checks.append('Toolchain paths/detection + secret masking + WSL path')
            # Error/retry state is a real HTTP failure, deliberately injected by the test.
            def failed(r):r.fulfill(status=500,content_type='application/json',body=json.dumps({'error':'Fixture: biblioteca nu este disponibilă; reîncearcă.'}))
            context.route('**/api/library',failed);page.locator('#nav button').filter(has_text=__import__('re').compile('^Library$')).click();page.wait_for_selector('#retry-page');assert 'Fixture' in page.locator('.error-state').inner_text();context.unroute('**/api/library',failed);page.locator('#retry-page').click();page.wait_for_function('()=>!studioUI.busy');checks.append('Page error and retry states')
            nav('Outputs');page.wait_for_selector('.output-table');page.locator('[data-output$=".mp4"]').first.click();page.wait_for_selector('#outputpreview video');page.wait_for_function('()=>document.querySelector("#outputpreview video").videoWidth>0');page.locator('[data-hash]').first.click();page.wait_for_function("()=>document.querySelector('#notice').textContent.includes('SHA256 calculat')");page.locator('[data-copy-path]').first.click();assert 'wsl.localhost' in page.evaluate('()=>navigator.clipboard.readText()');checks.append('Output video/verify badge/size/hash/date/copy Windows path')
            # All navigation pages and empty material states have a visible outcome.
            for name in ['Dashboard','Materials','Text / TTS','Split Text','Alignment','CTC Review','Scenes','Assets','Library','Subtitles','Audio Mix','Titles / Thumbnail','Split / Merge','Render','Workflow','Jobs','Logs','Verify','Review','Outputs','Settings']:
                nav(name);assert page.locator('h1').count();checks.append('Page '+name)
            nav('Scenes');material('');page.wait_for_function('()=>!studioUI.busy');assert 'Alege un material' in page.locator('#page').inner_text();checks.append('No-material empty state')
            assert not errors,errors;assert not external,external
            version=browser.version;browser.close();browser=None
        # HTTP security stays intact with the new preview/audio surfaces.
        for url in ['/api/paths?path=/etc','/api/scene-source?id=../bad&scene=x','/files?path=.git/config']:
            try:http(url);raise AssertionError('Unsafe GET accepted')
            except HTTPError as e:assert e.code==400
        for body in [dict(engine='studio',command=['toolchain-check'],values={'executable':'/bin/sh'}),dict(engine='studio',command=['audio-import'],values={'path':'/etc/passwd','tags':['music']})]:
            try:http('/api/jobs',body);raise AssertionError('Unsafe POST accepted')
            except HTTPError as e:assert e.code==400
        checks.append('Preview/audio/toolchain path boundaries')
        for p in (project/'work/studio/jobs').rglob('*'):
            if p.is_file() and p.suffix in ('.json','.log','.stderr','.stdout'):
                assert secret not in p.read_text(errors='replace'),str(p)
        checks.append('No API key in receipts/logs')
        assert (project/'materials/assets-integral-20261018/material.json').read_bytes()==before_full
        assert (project/'materials/studio-sample/material.json').read_bytes()==before_sample
        from datetime import datetime,timezone
        result=dict(utc=datetime.now(timezone.utc).isoformat(),version='1.1.0',technical_status='passed',browser_review='passed',browser=version,checks=checks,js_errors=errors,external_requests=external,offline_namespace=args.offline_namespace,crop=first,trim=trim,transition=transition,audio=audio,toolchain=tools,visual_sample_review='not_reviewed',listening_review='not_listened',editorial_review='not_reviewed',ctc_human_review='pending')
        (report/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(checks=checks,browser=version,js_errors=errors,external_requests=external),ensure_ascii=False))
    except Exception as error:
        try:
            (report/'failure-checks.json').write_text(json.dumps(dict(error=str(error),checks=checks,js_errors=errors),ensure_ascii=False,indent=2))
        except Exception:pass
        raise
    finally:
        if browser is not None:
            try:browser.close()
            except Exception:pass
        if server.poll() is None:server.terminate();server.wait(timeout=10)
        out.close();err.close()

if __name__=='__main__':main()
