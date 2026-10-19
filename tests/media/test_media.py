import json
import math
import os
from pathlib import Path
import struct
import subprocess
import wave

import pytest
from PIL import Image
from rec_media import core,content,derive,video

REPO=core.ROOT


@pytest.fixture
def material(tmp_path,monkeypatch):
    monkeypatch.setattr(core,'ROOT',tmp_path)
    monkeypatch.setattr(video,'ROOT',tmp_path)
    monkeypatch.setattr(derive,'ROOT',tmp_path)
    monkeypatch.setenv('PATH',os.environ['PATH']+os.pathsep+str(REPO/'.tools/ffmpeg'))
    rate=22050;frames=round(rate*2.4)
    audio=tmp_path/'sunet ș cu apostrof\' $.wav'
    # Synthetic pulses, not spoken words; timestamps are fixture data, not forced alignment.
    with wave.open(str(audio),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate)
        f.writeframes(b''.join(struct.pack('<h',round(3000*math.sin(2*math.pi*330*n/rate))) for n in range(frames)))
    text=tmp_path/'text.txt';text.write_text('Ștefan citește. Măriuca ascultă.',encoding='utf-8')
    image=tmp_path/'imagine ș cu spații.png';Image.new('RGB',(640,480),'#287088').save(image)
    document,m=core.init('fixture',audio,text,image)
    c=core.config(REPO/'media.json')
    c.update(profiles={'custom':[320,240]},subtitle_font_size=24,font_min=12,thumbnail_font_size=30)
    alignment=tmp_path/'cuvinte.json'
    alignment.write_text(json.dumps(dict(sample_rate=rate,audio_timeline_hash=core.key(m['timeline']),words=[
        dict(spoken=w,start=round(i*.6*rate),end=round((i*.6+.5)*rate)) for i,w in enumerate(m['text_spoken'].split())]),ensure_ascii=False))
    return document,m,c,image,alignment


def test_profiles_validation(material):
    _,_,c,_,_=material
    assert core.profiles('landscape,portrait',core.config(REPO/'media.json'))=={'landscape':[1920,1080],'portrait':[1080,1920]}
    for w,h in [(321,240),(0,240),(10000,100),('320',240)]:
        with pytest.raises(ValueError):core.profiles('custom',c,w,h)


def test_alignment_and_modes(material,tmp_path):
    p,m,c,image,path=material
    a=content.import_alignment(p,path,'synthetic fixture; unreviewed')
    _,m=core.load(p)
    assert m['alignment_status']=='imported_not_reviewed'
    for mode in ['classic','highlight','scroll']:
        files=content.subtitle_files(p,m,tmp_path/mode,[320,240],c,mode)
        ass=(tmp_path/mode/'subtitles.ass').read_text()
        assert 'Ștefan' in ass and 'Măriuca' in ass
        assert files['mode']==mode
    m['timeline'][0]['end']-=1
    with pytest.raises(ValueError):content.valid_words(m)


def test_alignment_wrong_text_and_overlap(material):
    p,m,c,image,path=material
    d=core.read(path);d['words'][0]['spoken']='inventat';core.write(path,d)
    with pytest.raises(ValueError,match='exact'):content.import_alignment(p,path,'fixture')
    d['words'][0]['spoken']='Ștefan';d['words'][1]['start']=0;core.write(path,d)
    with pytest.raises(ValueError,match='Intervale'):content.import_alignment(p,path,'fixture')


def test_split_strict_maximum_conflicts_and_roundtrip(material,tmp_path):
    p,m,c,image,path=material
    content.import_alignment(p,path,'synthetic fixture')
    _,m,plan=derive.split_plan(p,maximum=1.0)
    assert plan['intervals'][0][0]==0 and plan['intervals'][-1][1]==m['frames']
    assert all(b-a<=22050 for a,b in plan['intervals'])
    assert all(left[1]==right[0] for left,right in zip(plan['intervals'],plan['intervals'][1:]))
    children=derive.apply_split(p,plan,'strict')
    assert sum(core.load(child)[1]['frames'] for child in children)==m['frames']
    assert ' '.join(core.load(child)[1]['text_spoken'] for child in children).split()==m['text_spoken'].split()
    with pytest.raises(ValueError,match='Conflict durată maximă'):derive.split_plan(p,maximum=.1)
    with pytest.raises(ValueError,match='Conflict durată maximă'):derive.split_plan(p,intervals=[[0,m['frames']]],maximum=1)
    with pytest.raises(ValueError,match='Conflict durată maximă'):derive.split_plan(p,parts=1,maximum=1)
    for invalid in [float('nan'),float('inf'),0,-1,True,1e-12]:
        with pytest.raises(ValueError):derive.split_plan(p,maximum=invalid)
    # A changed strict ceiling in the plan is checked again before child creation.
    plan['maximum_seconds']=.1
    with pytest.raises(ValueError):derive.apply_split(p,plan,'bad-strict')
    assert not (p.parent.parent/'bad-strict-001').exists()


def test_titles_and_thumbnail(material,tmp_path):
    p,m,c,image,path=material
    t=content.titles(p,c)
    assert len(t['candidates'])==2
    content.titles(p,c,manual='Ștefan citește.',approve=True)
    assert content.titles(p,c)['selected']['title']=='Ștefan citește.'
    with pytest.raises(ValueError,match='blocat'):content.titles(p,c,manual='Înlocuire')
    outputs=content.thumbnail(p,tmp_path/'thumbs',{'custom':[320,240]},c,image=image)
    assert Image.open(outputs[0]).size==(320,240)
    with pytest.raises(ValueError):content.thumbnail(p,tmp_path/'bad',{'custom':[64,64]},c,text='x'*100)


def test_split_merge_exact_pcm_and_common_renderer(material,tmp_path):
    p,m,c,image,path=material
    content.import_alignment(p,path,'fixture')
    _,m,plan=derive.split_plan(p,parts=2)
    paths=derive.apply_split(p,plan,'fragment')
    q=derive.merge(paths,'compilatie')
    q,joined=core.load(q)
    assert joined['frames']==m['frames']
    original=core.assemble(p,m,tmp_path/'original.wav');combined=core.assemble(q,joined,tmp_path/'joined.wav')
    raw=[]
    for f in (original,combined):
        out=tmp_path/(f.stem+'.s32')
        core.ff(['-i',f,'-f','s32le',out]);raw.append(out.read_bytes())
    assert raw[0]==raw[1]
    assert len(joined['alignment']['words'])==4
    for value in [p,paths[0],q]:
        result=video.render(value,{'custom':[320,240]},c,subtitles='highlight')
        assert result['technical_status']=='passed'
        assert result['outputs'][0]['verification']['av_difference_seconds']<=.1


def test_gap_or_word_cut_rejected(material):
    p,m,c,image,path=material
    with pytest.raises(ValueError):derive.split_plan(p,intervals=[[1,m['frames']]])
    content.import_alignment(p,path,'fixture')
    with pytest.raises(ValueError,match='cuvânt'):derive.split_plan(p,intervals=[[0,100],[100,m['frames']]])


def test_render_static_protection_and_profiles(material):
    p,m,c,image,path=material
    r=video.render(p,{'custom':[320,240]},c)
    output=Path(r['outputs'][0]['path']);before=core.sha(output)
    assert video.render(p,{'custom':[320,240]},c)['outputs'][0]['already_complete']
    c['crf']=24
    with pytest.raises(ValueError,match='existent'):video.render(p,{'custom':[320,240]},c)
    assert core.sha(output)==before
    r=video.render(p,{'custom':[320,240]},c,force=True)
    assert r['outputs'][0]['verification']['format']['width']==320


def test_scenes_motion_transition_and_missing(material,tmp_path):
    p,m,c,image,path=material
    frame=m['frames']//2
    plan=tmp_path/'scene.json'
    core.write(plan,{'scenes':[dict(id='a',start=0,end=frame,path=str(image),kind='image',anchor='Ștefan',motion='zoom_in'),
                               dict(id='b',start=frame,end=m['frames'],path=str(image),kind='image',anchor='Măriuca',motion='pan',transition='crossfade')]})
    video.import_scenes(p,plan)
    r=video.render(p,{'custom':[320,240]},c,title='Ștefan citește.')
    assert r['technical_status']=='passed'
    image.write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='modificată'):video.render(p,{'custom':[320,240]},c,force=True)


def test_crossfade_keeps_padding_frames_and_blends_pixels(material,tmp_path):
    p,m,c,image,path=material
    Image.new('RGB',(640,480),'red').save(image)
    blue=tmp_path/'blue.png';Image.new('RGB',(640,480),'blue').save(blue)
    plan=tmp_path/'colors.json';middle=m['frames']//2
    core.write(plan,dict(scenes=[
        dict(id='red',start=0,end=middle,path=str(image),kind='image',anchor='Ștefan',motion='zoom_in'),
        dict(id='blue',start=middle,end=m['frames'],path=str(blue),kind='image',anchor='Măriuca',motion='pan',transition='crossfade')]))
    video.import_scenes(p,plan)
    destination=tmp_path/"exports ș ' alternative"
    result=video.render(p,{'custom':[320,240]},c,output_root=destination)
    output=Path(result['outputs'][0]['path'])
    assert output==destination/'fixture/custom/video.mp4'
    assert not (tmp_path/'output/media/fixture').exists()
    clip=tmp_path/'work/media/runs'/result['run_id']/'custom/scene-00000.mkv'
    info=json.loads(core.run([core.tool('ffprobe'),'-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=nb_read_frames','-of','json',clip]))
    assert int(info['streams'][0]['nb_read_frames'])==36+round(c['fps']*c['transition_seconds'])
    pixels=[]
    for i,t in enumerate([1.2+1/30,1.3,1.2+5/30]):
        frame=tmp_path/f'blend-{i}.png'
        core.ff(['-ss',str(t),'-i',output,'-frames:v','1',frame])
        with Image.open(frame) as rendered:pixels.append(rendered.convert('RGB').getpixel((160,120)))
    assert pixels[0][0]>pixels[1][0]>pixels[2][0]
    assert pixels[0][2]<pixels[1][2]<pixels[2][2]
    assert all(50<channel<200 for channel in (pixels[1][0],pixels[1][2]))


def test_no_alignment_no_fake_subtitles(material):
    p,m,c,image,path=material
    with pytest.raises(ValueError,match='alinierea reală'):video.render(p,{'custom':[320,240]},c,subtitles='classic')
    assert video.render(p,{'custom':[320,240]},c,plan_only=True)['technical_status']=='planned'


def test_static_picture_keeps_subsecond_caption_updates(material,tmp_path):
    import numpy as np
    p,m,c,image,path=material
    content.import_alignment(p,path,'constructed timing fixture')
    c['title_fade_seconds']=0
    result=video.render(p,{'custom':[320,240]},c,subtitles='highlight',title='Ștefan citește.')
    centroids=[]
    for index,time in enumerate((.2,.8)):
        frame=tmp_path/f'frame-{index}.png'
        core.ff(['-ss',str(time),'-i',result['outputs'][0]['path'],'-frames:v','1',frame])
        pixels=np.asarray(Image.open(frame).convert('RGB'))[120:]
        yellow=(pixels[:,:,0]>180)&(pixels[:,:,1]>180)&(pixels[:,:,2]<120)
        ys,xs=np.where(yellow)
        assert len(xs)>10
        centroids.append(float(xs.mean()))
    assert abs(centroids[0]-centroids[1])>20


def test_automatic_alignment_requires_supported_text_and_explicit_display_mapping(material):
    from rec_media import cli
    p,m,c,image,path=material
    m['text_spoken']=m['text_display']='Text cu ö.';core.write(p,m)
    args=cli.parser().parse_args(['--config',str(REPO/'media.json'),'align',str(p),'--backend','ctc-ro'])
    with pytest.raises(ValueError,match='Caractere fără suport'):cli.execute(args)
    m['text_spoken']='două mii';m['text_display']='2000';core.write(p,m)
    with pytest.raises(ValueError,match='maparea explicită'):cli.execute(args)


def test_merge_keeps_repeated_display_groups(material):
    p,m,c,image,path=material
    data=core.read(path)
    for word in data['words']:word.update(display='2026',display_group='year')
    core.write(path,data);content.import_alignment(p,path,'explicit display fixture')
    joined=derive.merge([str(p),str(p)],'repeated-year')
    _,m=core.load(joined)
    assert content.displayed(m['alignment']['words'])=='2026 2026'


def test_automatic_partition_prefers_inside_sentence_pause(material):
    p,m,c,image,path=material
    data=core.read(path);data['words'][2]['start']=round(1.5*m['sample_rate'])
    core.write(path,data);content.import_alignment(p,path,'constructed sentence pause')
    _,_,plan=derive.split_plan(p,parts=2)
    cut=plan['intervals'][0][1]
    assert cut==(data['words'][1]['end']+data['words'][2]['start'])//2
    assert data['words'][1]['end']<cut<data['words'][2]['start']


def test_manifest_paths_independent_cwd(material,tmp_path,monkeypatch):
    p,m,c,image,path=material
    monkeypatch.chdir('/tmp')
    assert core.checked(p,m['timeline'][0]['source']).is_file()
    assert core.load(p)[1]['id']=='fixture'


def test_media_interrupt_resume(material,monkeypatch):
    p,m,c,image,path=material
    original=video.verify
    count=0
    def interrupt(path,expected=None):
        nonlocal count
        count+=1
        if count==2:raise KeyboardInterrupt()
        return original(path,expected)
    monkeypatch.setattr(video,'verify',interrupt)
    with pytest.raises(KeyboardInterrupt):video.render(p,{'first':[320,240],'second':[240,320]},c)
    first=video.ROOT/'output/media/fixture/first/video.mp4'
    before=(core.sha(first),first.stat().st_mtime_ns)
    monkeypatch.setattr(video,'verify',original)
    result=video.render(p,{'first':[320,240],'second':[240,320]},c)
    assert result['outputs'][0]['already_complete']
    assert (core.sha(first),first.stat().st_mtime_ns)==before
    assert len(result['outputs'])==2


def test_batch_failure_resume_and_changed_inputs(material,tmp_path,monkeypatch):
    from rec_media import cli
    monkeypatch.setattr(cli,'ROOT',tmp_path)
    p,m,c,image,path=material
    cfg=tmp_path/'media.json';core.write(cfg,c)
    jobs=tmp_path/'batch.json'
    core.write(jobs,{'jobs':[{'args':['--config',str(cfg),'render',str(p),'--profiles','custom','--width','320','--height','240']},
                             {'args':['--config',str(cfg),'thumbnail',str(p),'--text','Ștefan citește.','--profiles','custom','--width','320','--height','240','--output-dir',str(tmp_path/'batch-thumbs')]},
                             {'args':['render','missing']} ]})
    args=cli.parser().parse_args(['--config',str(cfg),'batch',str(jobs)])
    first=cli.execute(args)
    assert first['technical_status']=='failed' and first['jobs'][2]['technical_status']=='failed'
    second=cli.execute(args)
    assert second['jobs'][0]['resumed'] and second['jobs'][1]['resumed']
    # Source/title changes invalidate a batch checkpoint; they must not silently skip.
    m=core.read(p);m['thumbnail_text']='Titlu diferit';core.write(p,m)
    third=cli.execute(args)
    assert not third['jobs'][1].get('resumed',False)


def test_video_source_and_custom_cover(material,tmp_path):
    p,m,c,image,path=material
    clip=tmp_path/'clip cu spații.mp4'
    core.ff(['-f','lavfi','-i','color=c=green:s=400x300:r=24:d=3','-c:v','libx264','-pix_fmt','yuv420p',clip])
    plan=tmp_path/'mixed.json'
    core.write(plan,{'scenes':[dict(id='one',start=0,end=m['frames']//2,path=str(image),kind='image',anchor='Ștefan'),
                               dict(id='two',start=m['frames']//2,end=m['frames'],path=str(clip),kind='video',anchor='Măriuca',fit='cover',focal=[.25,.75])]})
    video.import_scenes(p,plan)
    assert video.render(p,{'custom':[320,240]},c)['technical_status']=='passed'


def test_offline_render(material):
    p,m,c,image,path=material
    check=subprocess.run(['unshare','-Urn','true'],capture_output=True)
    if check.returncode:pytest.skip('Namespace de rețea indisponibil')
    import uuid
    m['id']='offline-'+uuid.uuid4().hex[:10];core.write(p,m)
    cfg=p.parent/'media.json';core.write(cfg,c)
    # Keep subprocess output and project lock inside the fixture, too.
    program='''import sys
from pathlib import Path
sys.path.insert(0,sys.argv.pop(1))
from rec_media import core,cli,derive,video
root=Path(sys.argv.pop(1))
core.ROOT=cli.ROOT=derive.ROOT=video.ROOT=root
raise SystemExit(cli.main(sys.argv[1:]))
'''
    result=subprocess.run(['unshare','-Urn','/usr/bin/python3','-c',program,str(REPO/'src'),str(p.parents[2]),'--config',str(cfg),'render',str(p),'--profiles','custom','--width','320','--height','240'],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)['technical_status']=='passed'


def test_display_spoken_mapping_and_ass_escaping(material,tmp_path):
    p,m,c,image,path=material
    m['text_spoken']='două mii douăzeci și șase';m['text_display']='2026';core.write(p,m)
    words=[dict(spoken=w,display='2026',display_group='year',start=i*9000,end=i*9000+8000) for i,w in enumerate(m['text_spoken'].split())]
    core.write(path,dict(sample_rate=m['sample_rate'],audio_timeline_hash=core.key(m['timeline']),words=words))
    content.import_alignment(p,path,'mapping fixture')
    _,m=core.load(p)
    content.subtitle_files(p,m,tmp_path/'map',[320,240],c,'highlight')
    srt=(tmp_path/'map/subtitles.srt').read_text();ass=(tmp_path/'map/subtitles.ass').read_text()
    assert srt.count('2026')==1
    assert ass.count(r'{\c&H00FFFF&}2026')==5
    assert content.ass_escape(r'{\pos(1,1)}')!=r'{\pos(1,1)}'


def test_invalid_material_id_and_focal_rejected(material):
    p,m,c,image,path=material
    m['id']='../../input';core.write(p,m)
    with pytest.raises(ValueError,match='ID'):core.load(p)
    m['id']='fixture';m['scenes'][0]['focal']=['0;bad',.5];core.write(p,m)
    with pytest.raises(ValueError,match='focal'):video.render(p,{'custom':[320,240]},c)


def test_resume_complete_scenes_after_interrupted_atomic_publication(material,tmp_path,monkeypatch):
    p,m,c,image,_=material
    middle=m['frames']//2
    plan=tmp_path/'recovery-scenes.json'
    core.write(plan,dict(scenes=[
        dict(id='one',start=0,end=middle,path=str(image),kind='image',anchor='Ștefan',motion='zoom_in'),
        dict(id='two',start=middle,end=m['frames'],path=str(image),kind='image',anchor='Măriuca',motion='pan',transition='crossfade')]))
    video.import_scenes(p,plan)
    original=video.logged_ff
    parts=[]
    def interrupt(args,folder,label):
        # Actual interrupted MP4 header: ftyp, free, empty mdat, no moov.
        part=Path(args[-1]);part.write_bytes(bytes.fromhex('000000206674797069736f6d0000020069736f6d69736f32617663316d7034310000000866726565000000006d646174'));parts.append(part)
        raise KeyboardInterrupt('simulated final encoder interruption')
    monkeypatch.setattr(video,'logged_ff',interrupt)
    with pytest.raises(KeyboardInterrupt):video.render(p,{'custom':[320,240]},c)
    run=next((tmp_path/'work/media/runs').iterdir())
    scenes=sorted((run/'custom').glob('scene-*.mkv'))
    before={s:(core.sha(s),s.stat().st_mtime_ns) for s in scenes};assert len(before)==2
    output=tmp_path/'output/media/fixture/custom/video.mp4';assert not output.exists()
    incomplete_hash=core.sha(parts[0])
    with pytest.raises(ValueError,match='moov atom not found'):video.probe(parts[0])
    monkeypatch.setattr(video,'logged_ff',original)
    real_ff=video.ff
    def forbid_scene_render(args,*a,**kw):
        assert not (str(args[-1]).endswith('.mkv') and '-c:v' in args), 'valid scene was rerendered'
        return real_ff(args,*a,**kw)
    monkeypatch.setattr(video,'ff',forbid_scene_render)
    real_replace=video.os.replace;publications=[]
    def atomic_replace(source,target):
        if Path(target)==output:
            assert Path(source).parent==output.parent and not output.exists()
            assert video.verify(source)['full_decode'];publications.append((source,target))
        return real_replace(source,target)
    monkeypatch.setattr(video.os,'replace',atomic_replace)
    resumed=video.render(p,{'custom':[320,240]},c,resume_run=run.name)
    assert resumed['outputs'][0]['verification']['full_decode'] and len(publications)==1
    assert {s:(core.sha(s),s.stat().st_mtime_ns) for s in scenes}==before
    assert parts[0].stat().st_size==48 and parts[0]!=output
    assert core.sha(parts[0])==incomplete_hash
    assert len(core.read(run/'run.json')['reused_scenes'])==2
    command=core.read(next((run/'custom').glob('final-*.command.json')))
    assert command['phase']=='complete' and command['returncode']==0
    cursor=0
    for i,arg in enumerate(command['args']):
        if arg=='-i':
            assert '-threads' in command['args'][cursor:i]
            cursor=i+2
    # An encoding-relevant change cannot silently adopt existing intermediates.
    c['motion_amount']=.1
    with pytest.raises(ValueError,match='receipt compatible|receipt compatibil|existent'):
        video.render(p,{'custom':[320,240]},c,resume_run=run.name,output_root=tmp_path/'incompatible')



def test_failed_final_command_keeps_exact_stderr_and_returncode(material,tmp_path):
    folder=tmp_path/'diagnostic';folder.mkdir()
    missing=folder/'missing-input.mkv'
    with pytest.raises(ValueError,match='FFmpeg final: exit 254|FFmpeg final: exit 1'):
        video.logged_ff(['-i',missing,'-f','null','-'],folder,'final')
    receipt=next(folder.glob('final-*.command.json'));result=core.read(receipt)
    assert result['phase']=='failed' and result['returncode']!=0
    assert result['cwd']==str(folder) and str(missing) in result['args']
    assert 'missing-input.mkv' in receipt.with_suffix('.stderr').read_text()


def test_recovery_after_process_exit_with_three_valid_scenes(material,tmp_path):
    """A hard process exit leaves running state, receipts and a 48-byte MP4."""
    p,m,c,image,_=material
    plan=tmp_path/'three-scenes.json';a=m['frames']//3;b=2*a
    core.write(plan,dict(scenes=[
        dict(id='a',start=0,end=a,path=str(image),kind='image',anchor='Ștefan',motion='zoom_in'),
        dict(id='b',start=a,end=b,path=str(image),kind='image',anchor='citește.',motion='pan',transition='crossfade'),
        dict(id='c',start=b,end=m['frames'],path=str(image),kind='image',anchor='Măriuca',motion='zoom_out',transition='crossfade')]))
    video.import_scenes(p,plan)
    child=r'''
import json,os,sys
from pathlib import Path
from rec_media import core,video
core.ROOT=video.ROOT=Path(sys.argv[1])
c=json.loads(sys.argv[3]);mode=sys.argv[4]
if mode=='interrupt':
 def interrupted_final(args,folder,label):
  Path(args[-1]).write_bytes(bytes.fromhex('000000206674797069736f6d0000020069736f6d69736f32617663316d7034310000000866726565000000006d646174'))
  os._exit(1)
 video.logged_ff=interrupted_final
else:
 real_ff=video.ff
 def forbid_rerender(args,*a,**kw):
  assert not (str(args[-1]).endswith('.mkv') and '-c:v' in args)
  return real_ff(args,*a,**kw)
 video.ff=forbid_rerender
run=None if mode=='interrupt' else sys.argv[5]
print(json.dumps(video.render(sys.argv[2],{'custom':[320,240]},c,resume_run=run)))
'''
    env={**os.environ,'PYTHONPATH':str(REPO/'src')+os.pathsep+'/usr/lib/python3/dist-packages'}
    args=[__import__('sys').executable,'-c',child,str(tmp_path),str(p),json.dumps(c)]
    failed=subprocess.run([*args,'interrupt'],env=env,capture_output=True,text=True)
    assert failed.returncode==1 and not failed.stderr,failed.stderr
    run=next((tmp_path/'work/media/runs').iterdir())
    assert core.read(run/'run.json')['phase']=='running'
    scenes=list((run/'custom').glob('scene-*.mkv'));assert len(scenes)==3
    before={s:(core.sha(s),s.stat().st_mtime_ns) for s in scenes}
    parts=list((tmp_path/'output/media/fixture/custom').glob('*.part.mp4'))
    assert len(parts)==1 and parts[0].stat().st_size==48
    incomplete_hash=core.sha(parts[0])
    assert not (parts[0].parent/'video.mp4').exists()
    resumed=subprocess.run([*args,'resume',run.name],env=env,capture_output=True,text=True)
    assert resumed.returncode==0,resumed.stderr
    result=json.loads(resumed.stdout)
    assert result['technical_status']=='passed' and result['outputs'][0]['verification']['full_decode']
    assert {s:(core.sha(s),s.stat().st_mtime_ns) for s in scenes}==before
    assert parts[0].stat().st_size==48
    assert core.sha(parts[0])==incomplete_hash
    assert core.read(run/'run.json')['phase']=='complete'


def test_split_merge_rebases_scene_text_anchors_and_unicode_ranges(material):
    p,m,c,image,path=material
    content.import_alignment(p,path,'constructed timing fixture')
    _,_,plan=derive.split_plan(p,parts=2)
    children=derive.apply_split(p,plan,'mapped')
    for child in children:
        _,cm=core.load(child)
        assert len(cm['scenes'])==1
        scene=cm['scenes'][0];a,b=scene['text_range']
        assert cm['text_spoken'][a:b]==scene['anchor']==cm['text_spoken']
        assert scene['text_mapping_history'][0]['anchor']==m['text_spoken']
    joined=derive.merge([children[1],children[0],children[1]],'mapped-repeated')
    _,jm=core.load(joined)
    previous=-1
    for scene in jm['scenes']:
        a,b=scene['text_range']
        assert previous<a<b and jm['text_spoken'][a:b]==scene['anchor']
        previous=a
    assert jm['scenes'][0]['anchor']==jm['scenes'][2]['anchor']
    assert jm['scenes'][0]['text_range']!=jm['scenes'][2]['text_range']
    # Metadata rebasing must leave the visual inputs and sample intervals intact.
    assert all(s['asset']['sha256']==m['scenes'][0]['asset']['sha256'] for s in jm['scenes'])
    snapshot=__import__('copy').deepcopy(jm['scenes']);derive.map_scene_text(jm)
    assert jm['scenes']==snapshot
