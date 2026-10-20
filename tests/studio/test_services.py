"""Isolated parity, input boundaries and recovery: no private production writes."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil
import struct
import wave
import pytest
from rec_media import core,cli,services,asset_scenes,video,derive
from rec_media.studio import catalog,security,operations,jobs

REPO=Path(__file__).resolve().parents[2]

@pytest.fixture
def project(tmp_path,monkeypatch):
    for module in [core,cli,services,video,derive]:monkeypatch.setattr(module,'ROOT',tmp_path)
    for name in ['input','output','samples','assets','materials','work']:(tmp_path/name).mkdir()
    shutil.copy2(REPO/'media.json',tmp_path/'media.json');shutil.copy2(REPO/'rec.json',tmp_path/'rec.json')
    (tmp_path/'.tools').symlink_to(REPO/'.tools')
    from PIL import Image
    audio=tmp_path/'input/source.wav'
    with wave.open(str(audio),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(22050);f.writeframes(struct.pack('<h',1000)*22050)
    text=tmp_path/'input/source.txt';text.write_text('Text de probă.')
    image=tmp_path/'input/image.png';Image.new('RGB',(320,180),'red').save(image)
    p,m=core.init('fixture',audio,text,image)
    return tmp_path,p,m


def test_catalog_exact_cli_inventory():
    rows=catalog.catalog('media');names={r['command'][0] for r in rows}
    from rec_media.cli import parser
    actual=next(a for a in parser()._actions if isinstance(a,argparse._SubParsersAction)).choices
    assert names==set(actual)
    assert {r['command'][0] for r in catalog.catalog('tts')}=={'doctor','prepare','preview','render','verify','fetch-model'}


def test_shared_dispatch_is_identical(project):
    root,p,m=project
    a=cli.parser().parse_args(['--config',str(root/'media.json'),'scenes','fixture','--inspect'])
    req=operations.prepare_request(dict(engine='media',command=['scenes'],values=dict(material='fixture',inspect=True)),root/'work/request')
    assert cli.execute(a)==operations.run_request(req)==services.execute(a)


def test_scene_edit_cli_gui_same_manifest_and_pixel_key(project):
    root,p,m=project
    settings=dict(visual=dict(fit='cover',focal_point=[.2,.7],motion='zoom_in'))
    config=root/'input/scene.json';core.write(config,settings)
    a=cli.parser().parse_args(['scenes','fixture','--scene','scene-001','--profile','portrait','--set',str(config)])
    cli.execute(a);after_cli=core.read(p)
    core.write(p,m)
    req=operations.prepare_request(dict(engine='media',command=['scenes'],values=dict(material='fixture',scene='scene-001',profile='portrait'),inline=dict(set=settings)),root/'work/request')
    operations.run_request(req);after_gui=core.read(p)
    # Timestamp and revision identity are observations; effective rendering config must be exact.
    s1=asset_scenes.effective(after_cli['scenes'][0],'portrait');s2=asset_scenes.effective(after_gui['scenes'][0],'portrait')
    assert s1['visual']==s2['visual'] and s1['asset']==s2['asset']
    c=core.config();assert operations.scene_keys(after_cli,c,[1080,1920],'portrait')==operations.scene_keys(after_gui,c,[1080,1920],'portrait')


@pytest.mark.parametrize('value',['../secret','/etc/passwd','.git/config','input/../../etc/passwd','src/rec_media/core.py'])
def test_path_escape_refused(project,value):
    with pytest.raises(ValueError):security.path(value)


def test_symlink_escape_refused(project,tmp_path):
    root,p,m=project;(root/'input/outside').symlink_to('/etc')
    with pytest.raises(ValueError):security.path('input/outside/passwd')


@pytest.mark.parametrize('command',[['gui'],['workflow'],['batch'],['fetch-model'],['render;rm']])
def test_no_shell_or_nested_unvalidated_commands(project,command):
    with pytest.raises(ValueError):operations.prepare_request(dict(engine='media',command=command,values={}),project[0]/'work/request')


def test_embedded_json_path_checked_before_mutation(project):
    root,p,m=project;before=core.sha(p)
    with pytest.raises(ValueError):operations.prepare_request(dict(engine='media',command=['audio-mix'],values=dict(material='fixture'),inline=dict(set=dict(enabled=True,tracks=[dict(type='music',path='/etc/passwd')]))),root/'work/request')
    assert core.sha(p)==before


def test_text_draft_does_not_change_audio_or_alignment(project):
    root,p,m=project;before=p.read_bytes();audio=core.checked(p,m['timeline'][0]['source']);digest=core.sha(audio)
    t=operations.text_state('fixture');r=operations.save_text('fixture','Alt text.',t['sha256'])
    assert r['diff'] and p.read_bytes()==before and core.sha(audio)==digest
    with pytest.raises(ValueError):operations.save_text('fixture','race',t['sha256'])


def test_subtitle_edit_preserves_scene_key_and_undo(project):
    root,p,m=project;c=core.config();before=operations.scene_keys(m,c,[1920,1080],'landscape')
    operations.save_subtitles('fixture',dict(preset='boxed',font_size=40,profiles=dict(portrait=dict(margin_v=.12))))
    _,updated=core.load(p);assert operations.scene_keys(updated,core.config(overrides=updated['composition']),[1920,1080],'landscape')==before
    operations.save_subtitles('fixture',{},undo=True);assert core.read(p)['composition']['subtitle_style']=={}


def test_safe_duplicate_preserves_sources(project):
    root,p,m=project;before=core.sha(p);operations.duplicate('fixture','copied');q,n=core.load('copied')
    assert core.sha(p)==before and n['exports']==[] and n['id']=='copied'
    assert core.checked(q,n['timeline'][0]['source'])==core.checked(p,m['timeline'][0]['source'])


def test_invalid_style_and_ids_refused(project):
    with pytest.raises(ValueError):operations.save_subtitles('fixture',dict(font_size=-1))
    with pytest.raises(ValueError):operations.duplicate('fixture','../bad')


def test_secret_redaction():
    assert security.public(dict(PEXELS_API_KEY='secret',nested=dict(Authorization='secret'))) == {'PEXELS_API_KEY':'[REDACTED]','nested':{'Authorization':'[REDACTED]'}}


def test_process_identity_is_required_for_cancel():
    import os
    assert jobs.alive(dict(pid=os.getpid(),process_identity=jobs.process_identity(os.getpid())))
    assert not jobs.alive(dict(pid=os.getpid(),process_identity='wrong'))


def test_render_plan_does_not_write_export(project):
    root,p,m=project;r=operations.render_plan(dict(material='fixture',profiles='landscape',subtitles='off'))
    assert r['profiles']['landscape']['requires_render']==1
    assert not list((root/'output').rglob('*.mp4'))


def test_inline_audio_paths_use_project_root(project):
    root,p,m=project
    r=operations.prepare_request(dict(engine='media',command=['audio-mix'],values=dict(material='fixture'),
       inline=dict(validate=dict(enabled=True,tracks=[dict(type='music',path='input/source.wav',volume_db=-20)]))),root/'work/job')
    imported=core.read(r['values']['validate'])
    assert imported['tracks'][0]['path']==str(root/'input/source.wav')
    result=operations.run_request(r)
    assert result['validation_only'] and core.read(p)==m


def test_tts_cli_and_gui_share_preparation(project,monkeypatch,capsys):
    root,p,m=project
    from rec_tts import cli as tcli, services as tservices,common
    monkeypatch.setattr(tcli,'ROOT',root)
    monkeypatch.setattr(tservices,'project_lock',lambda:common.project_lock(root))
    core.write(root/'pronunciations.json',[])
    source=root/'input/source.txt'
    assert tcli.main(['prepare',str(source),'--output-dir',str(root/'output/cli')])==0
    req=operations.prepare_request(dict(engine='tts',command=['prepare'],values=dict(input=str(source),output_dir=str(root/'output/gui'))),root/'work/job')
    result=operations.run_request(req)
    assert result['segments']>0
    for name in ['normalized.txt','segments.json','warnings.json']:
        assert (root/'output/cli'/name).read_bytes()==(root/'output/gui'/name).read_bytes()


def test_local_playlist_cannot_trigger_network(project):
    root,p,m=project;playlist=root/'input/disguised.wav'
    playlist.write_text('#EXTM3U\nhttps://example.invalid/private\n')
    with pytest.raises(ValueError,match='Container'):
        operations.prepare_request(dict(engine='media',command=['init'],values=dict(id='evil',audio=str(playlist))),root/'work/job')


def test_progress_never_adopts_another_material_run(project):
    root,p,m=project;q=jobs.Queue.__new__(jobs.Queue);q.root=root/'work/studio/jobs'
    jid='a'*32;folder=q.root/jid
    core.write(folder/'job.json',dict(id=jid,status='queued',request=dict(command=['render']),started=None,material='fixture'))
    core.write(root/'work/media/runs'/('b'*32)/'run.json',dict(plan=dict(material='fixture',scene_count=1,profiles={'landscape':[1920,1080]}),phase='running',rendered_scenes=['scene.mkv']))
    detail=q.detail(jid)
    assert not detail.get('run_id') and not detail.get('progress')


def test_observer_is_called_under_shared_lock(project):
    root,p,m=project;observed=[]
    def observer():
        with pytest.raises(ValueError):
            with core.lock():pass
        observed.append(True)
    a=cli.parser().parse_args(['scenes','fixture','--inspect'])
    services.run(a,on_locked=observer)
    assert observed==[True]


def test_workflow_nested_paths_are_normalized_and_bounded(project):
    root,p,m=project;plan=root/'input/workflow.json'
    core.write(plan,dict(steps=[dict(id='inspect',tool='media',args=['scenes','fixture','--inspect'],inputs=['source.txt'],outputs=[])]))
    request=operations.prepare_request(dict(engine='media',command=['workflow'],values=dict(plan=str(plan))),root/'work/job')
    normalized=core.read(request['values']['plan']);assert normalized['steps'][0]['inputs']==[str(root/'input/source.txt')]
    assert '--config' in normalized['steps'][0]['args']
    core.write(plan,dict(steps=[dict(id='bad',tool='media',args=['verify','/etc/passwd'])]))
    with pytest.raises(ValueError):operations.prepare_request(dict(engine='media',command=['workflow'],values=dict(plan=str(plan))),root/'work/job')


def test_workflow_cannot_hide_network_or_recursion(project):
    root,p,m=project;plan=root/'input/workflow.json'
    for args in [['workflow',str(plan)],['assets','search','fixture','--scene','scene-001']]:
        core.write(plan,dict(steps=[dict(id='bad',tool='media',args=args)]))
        with pytest.raises(ValueError):operations.prepare_request(dict(engine='media',command=['workflow'],values=dict(plan=str(plan))),root/'work/job')


def test_job_state_updates_do_not_erase_worker_completion(project):
    root,*_=project;folder=root/'work/studio/jobs'/('a'*32)
    core.write(folder/'job.json',dict(id='a'*32,status='running',pid=123,started='2026-10-20T00:00:00+00:00'))
    jobs.update_job(folder,dict(status='complete',finished='2026-10-20T00:00:01+00:00'))
    jobs.update_job(folder,dict(worker_returncode=0,resumed_from='b'*32))
    result=core.read(folder/'job.json')
    assert result['status']=='complete' and result['pid']==123 and result['finished'].endswith('01+00:00')


def test_workflow_resume_keeps_existing_state_location(project):
    root,p,m=project;source=root/'input/workflow.json'
    core.write(source,dict(steps=[dict(id='inspect',tool='media',args=['scenes','fixture','--inspect'],inputs=[],outputs=[])]))
    first=operations.prepare_request(dict(engine='media',command=['workflow'],values=dict(plan=str(source))),root/'work/job1')
    resumed=operations.prepare_request(first,root/'work/job2')
    assert resumed['values']['plan']==first['values']['plan']
