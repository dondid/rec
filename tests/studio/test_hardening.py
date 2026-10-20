"""Hardening fixtures: isolated media, production backend, no TTS/CTC inference."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import os
import sqlite3
import subprocess
import pytest
from PIL import Image,ImageDraw,ImageChops
from test_services import project
from rec_media import core,asset_render,asset_scenes,asset_library,video
from rec_media.studio import previews,audio_library,platform_support,progress,operations


def request(**kw):return dict(material='fixture',scene='scene-001',profiles=['landscape','portrait'],**kw)


def striped(project):
    root,p,m=project;image=root/'input/image.png';im=Image.new('RGB',(400,200));draw=ImageDraw.Draw(im)
    for x in range(400):draw.line([(x,0),(x,199)],fill=(round(x*255/399),50,255-round(x*255/399)))
    im.save(image);m['scenes'][0]['asset']=core.reference(image,p);core.write(p,m)
    return root,p,m


def test_crop_preview_is_production_pixel_pipeline_and_source_is_immutable(project):
    root,p,m=striped(project);before=p.read_bytes();values=request(settings={'visual':{'fit':'cover','focal_point':[.2,.7],'crop':[.1,0,.9,1]}})
    result=previews.render(values);assert not result['cache_hit'] and len(result['outputs'])==2
    _,_,snapshot,_=previews.validate(values);c=core.config();c.pop('subtitle_style',None)
    for output in result['outputs']:
        profile=output['profile'];folder=root/'work/direct'/profile;folder.mkdir(parents=True)
        eff=asset_scenes.effective(snapshot,profile);clip=folder/'direct.mkv';core.ff(asset_render.generate(p,eff,output['size'],c,folder,clip,1,0))
        direct=folder/'direct.png';core.ff(['-threads','2','-i',clip,'-frames:v','1','-threads','2',direct])
        with Image.open(direct) as a,Image.open(output['path']) as b:assert ImageChops.difference(a.convert('RGB'),b.convert('RGB')).getbbox() is None
    assert p.read_bytes()==before
    again=previews.render(values);assert again['cache_hit'] and [o['sha256'] for o in again['outputs']]==[o['sha256'] for o in result['outputs']]


def test_profile_focal_preview_does_not_change_other_profile_or_scene_key(project):
    root,p,m=striped(project);c=core.config();before=operations.scene_keys(m,c,c['profiles']['landscape'],'landscape')
    baseline=previews.render(request());changed=previews.render(request(profile='portrait',settings={'visual':{'fit':'cover','focal_point':[1,0]}}))
    hashes=lambda r:{o['profile']:o['sha256'] for o in r['outputs']}
    assert hashes(baseline)['landscape']==hashes(changed)['landscape']
    assert hashes(baseline)['portrait']!=hashes(changed)['portrait']
    assert operations.scene_keys(core.read(p),c,c['profiles']['landscape'],'landscape')==before


def test_corrupt_preview_is_preserved_and_not_adopted(project):
    root,p,m=project;r=previews.render(request());bad=Path(r['outputs'][0]['path']);bad.write_bytes(b'broken')
    again=previews.render(request());assert not again['cache_hit'] and bad.read_bytes()==b'broken'
    assert again['outputs'][0]['path']!=str(bad)
    assert list((root/'work/studio/previews'/r['request']).glob('attempt-*/before-receipt.json'))


@pytest.mark.parametrize('extra',[{'profiles':['bad']},{'settings':{'visual':{'fit':'invented'}}},{'settings':{'video':{'audio_enabled':True}}},{'frame_time':float('nan')},{'settings':{'path':'/etc/passwd'}}])
def test_preview_rejects_unsupported_or_unsafe_controls(project,extra):
    values=request();values.update(extra)
    with pytest.raises(ValueError):previews.validate(values)


def video_fixture(project):
    root,p,m=project;clip=root/'input/clip.mp4'
    core.ff(['-f','lavfi','-i','testsrc2=s=320x180:r=24:d=2','-an','-c:v','libx264','-threads','2','-pix_fmt','yuv420p',clip])
    s=m['scenes'][0];s.update(kind='video',asset=core.reference(clip,p));core.write(p,m)
    return root,p,m


def test_video_trim_scrub_real_frame_and_mute(project):
    root,p,m=video_fixture(project);before=p.read_bytes()
    values=request(profile='landscape')
    values.update(profiles=['landscape'],settings=dict(video=dict(source_start=.25,source_end=1.75,audio_enabled=False),visual=dict(short_policy='freeze')),frame_time=.5,frame_profile='landscape')
    a=previews.render(values);meta=a['outputs'][0]['metadata'];assert meta['muted'] and meta['source_fps']==24 and meta['trim_duration']==1.5
    values['frame_time']=1.5;b=previews.render(values);assert a['outputs'][0]['sha256']!=b['outputs'][0]['sha256']
    values['frame_time']=1.75;end=previews.render(values);assert end['outputs'][0]['metadata']['effective_frame_time']<1.75
    assert p.read_bytes()==before
    values['frame_time']=2
    with pytest.raises(ValueError,match='Scrub'):previews.render(values)


def test_video_short_policy_is_visible_not_silently_changed(project):
    root,p,m=video_fixture(project);values=request(settings=dict(video=dict(source_start=0,source_end=.1),visual=dict(short_policy='error')))
    result=previews.render(values)
    assert all(o['metadata']['short_clip'] and not o['metadata']['render_ready'] for o in result['outputs'])
    assert all(o['metadata']['short_policy']=='error' for o in result['outputs'])


def transition_fixture(project,transition):
    root,p,m=project;other=root/'input/blue.png';Image.new('RGB',(320,180),'blue').save(other)
    first=m['scenes'][0];first['end']=m['frames']//2;second=deepcopy(first);second.update(id='scene-002',start=first['end'],end=m['frames'],asset=core.reference(other,p),transition=transition)
    m['scenes'].append(second);core.write(p,m);return root,p,m


@pytest.mark.parametrize('transition',['cut','crossfade'])
def test_transition_preview_real_frames_and_cache(project,transition):
    root,p,m=transition_fixture(project,transition);before=p.read_bytes()
    result=previews.render(dict(material='fixture',scene='scene-002',profiles=['landscape'],kind='transition'))
    output=result['outputs'][0];assert output['frames']==60 and output['muted']
    raw=subprocess.run([core.tool('ffmpeg'),'-nostdin','-v','error','-threads','2','-i',output['path'],'-vf','scale=1:1','-pix_fmt','rgb24','-f','rawvideo','-'],capture_output=True,check=True).stdout
    mixed=sum(1 for i in range(0,len(raw),3) if raw[i]>15 and raw[i+2]>15)
    assert mixed>=3 if transition=='crossfade' else mixed==0
    assert p.read_bytes()==before and previews.render(dict(material='fixture',scene='scene-002',profiles=['landscape'],kind='transition'))['cache_hit']


def test_first_scene_has_no_incoming_transition(project):
    with pytest.raises(ValueError,match='Prima scenă'):previews.render(request(kind='transition'))


def test_audio_library_real_metadata_dedup_and_legacy_compatibility(project):
    root,p,m=project
    with asset_library.Library() as lib:visual=lib.ingest(root/'input/image.png',dict(provider='local',license='unknown',creator='fixture'))
    values=dict(path='input/source.wav',tags=['music','ambience'],creator='fixture',license='unknown',source='local fixture')
    result=audio_library.import_audio(values);a=result['asset'];blob=Path(a['local_path']);stamp=blob.stat().st_mtime_ns
    assert a['frames']==22050 and a['sample_rate']==22050 and a['channels']==1 and a['duration']==1
    assert a['license']=='unknown' and a['listening_review']=='not_listened'
    assert audio_library.records('fixture','music')[0]['asset_id']==a['asset_id']
    again=audio_library.import_audio(values);assert again['asset']['checksum']==a['checksum'] and blob.stat().st_mtime_ns==stamp
    assert operations.library_records()[0]['checksum']==visual['checksum']
    with asset_library.Library() as lib:assert lib.get(visual['asset_id'])['type']=='image'


def test_audio_first_library_does_not_break_visual_empty_list(project):
    audio_library.import_audio(dict(path='input/source.wav',tags=['sfx']))
    assert operations.library_records()==[]


def test_audio_checksum_mismatch_refused_before_publication(project):
    root,p,m=project
    with pytest.raises(ValueError,match='Checksum'):audio_library.import_audio(dict(path='input/source.wav',tags=['music'],checksum='0'*64))
    assert not audio_library.records() and not list((root/'assets/library/objects').rglob('*'))


def test_audio_reuse_uses_same_mixer_and_provenance(project):
    root,p,m=project;a=audio_library.import_audio(dict(path='input/source.wav',tags=['sfx'],creator='fixture',license='unknown'))['asset']
    req=operations.prepare_request(dict(engine='media',command=['audio-mix'],values=dict(material='fixture'),inline=dict(validate=dict(enabled=True,tracks=[dict(type='sfx',path=a['local_path'],source='audio-library:'+a['asset_id'],creator=a['creator'],license=a['license'])]))),root/'work/request')
    result=operations.run_request(req);track=result['audio_mix']['tracks'][0]
    assert track['source']['sha256']==a['checksum'] and track['source']['creator']=='fixture' and track['source']['license']=='unknown'
    assert core.read(p)==m


def test_audio_invalid_tag_and_video_disguised_as_audio_refused(project):
    root,p,m=project
    with pytest.raises(ValueError):audio_library.import_audio(dict(path='input/source.wav',tags=['approved music']))
    video_fixture(project)
    # Video-only MP4 cannot be indexed as audio.
    with pytest.raises(ValueError):audio_library.import_audio(dict(path='input/clip.mp4',tags=['music']))


def test_progress_telemetry_preserves_decoded_pixels_and_exact_frames(project):
    root,p,m=project;folder=root/'work/progress';folder.mkdir();a=root/'output/a.mkv';b=root/'output/b.mkv'
    args=['-f','lavfi','-i','color=c=blue:s=64x64:r=30:d=0.3','-frames:v','9','-an','-c:v','ffv1','-threads','2']
    core.ff([*args,a])
    with progress.instrument(folder):core.ff([*args,b])
    result=progress.detail(folder);assert result['frame']==9 and result['expected_frames']==9 and result['percent']==100 and result['returncode']==0
    digest=lambda path:core.ff(['-i',path,'-map','0:v:0','-f','streamhash','-hash','sha256','-'])
    assert digest(a)==digest(b)
    meta=core.read(next((folder/'ffmpeg').glob('*.json')));assert '-progress' in meta['effective_argv'] and '-progress' not in meta['original_argv']


def test_progress_ignores_partial_blocks_and_unknown_eta(project):
    p=project[0]/'work/frames.progress';p.write_text('frame=3\nprogress=continue\nframe=4\n')
    assert progress.progress_block(p)['frame']=='3'
    assert progress.finite_number('N/A') is None


def test_scene_optimistic_lock_refuses_stale_saves(project):
    root,p,m=project;request_=dict(engine='media',command=['scenes'],values=dict(material='fixture',scene='scene-001'),inline={'set':{'visual':{'fit':'cover'}}},expected=core.sha(p))
    prepared=operations.prepare_request(request_,root/'work/request');m['history'].append({'action':'other editor'});core.write(p,m)
    with pytest.raises(ValueError,match='alt job'):operations.run_request(prepared)
    assert core.read(p)==m


def test_windows_path_presentation_and_scoped_access(project,monkeypatch):
    monkeypatch.setenv('WSL_DISTRO_NAME','Debian')
    assert platform_support.windows_path('/home/test/ș cu spații')=='\\\\wsl.localhost\\Debian\\home\\test\\ș cu spații'
    assert platform_support.windows_path('/mnt/c/Users/A B')=='C:\\Users\\A B'
    assert platform_support.paths('output')['windows_path'].endswith('\\output')
    with pytest.raises(ValueError):platform_support.paths('/etc')


def test_open_folder_failure_is_honest_and_uses_no_shell(project,monkeypatch):
    monkeypatch.setenv('WSL_DISTRO_NAME','Debian');monkeypatch.setattr(platform_support.shutil,'which',lambda name:'/mnt/c/explorer.exe' if name=='explorer.exe' else None)
    def blocked(args,**kwargs):assert isinstance(args,list) and not kwargs.get('shell');raise OSError('Interop unavailable')
    monkeypatch.setattr(platform_support.subprocess,'Popen',blocked)
    result=platform_support.open_folder('output');assert result['opened'] is False and result['status']=='interop_failed'


def test_explorer_exit_code_is_not_visual_confirmation(project,monkeypatch):
    monkeypatch.setenv('WSL_DISTRO_NAME','Debian')
    monkeypatch.setattr(platform_support.shutil,'which',lambda n:'/mnt/c/explorer.exe' if n=='explorer.exe' else None)
    class Process:
        pid=123
        def wait(self,timeout):return 1
    monkeypatch.setattr(platform_support.subprocess,'Popen',lambda *a,**k:Process())
    result=platform_support.open_folder('output')
    assert result['opened'] is None and result['status']=='launch_requested' and result['returncode']==1
