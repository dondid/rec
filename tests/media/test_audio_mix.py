"""Technical local fixtures only; no human listening or publication approval."""
from array import array
from copy import deepcopy
import math
import os
from pathlib import Path
import struct
import subprocess
import wave
import pytest
from PIL import Image
from rec_media import audio_mix as mix,core,derive,video

REPO=core.ROOT


def tone(path,rate=44100,channels=2,seconds=2,freq=1000,amplitude=.12,voiced=None):
    with wave.open(str(path),'wb') as f:
        f.setnchannels(channels);f.setsampwidth(2);f.setframerate(rate)
        f.writeframes(b''.join(struct.pack('<h',round(32767*amplitude*math.sin(2*math.pi*freq*n/rate)*(voiced(n/rate) if voiced else 1)))*channels for n in range(round(seconds*rate))))


@pytest.fixture
def audio(tmp_path,monkeypatch):
    monkeypatch.setattr(core,'ROOT',tmp_path);monkeypatch.setattr(video,'ROOT',tmp_path);monkeypatch.setattr(derive,'ROOT',tmp_path)
    monkeypatch.setenv('PATH',os.environ['PATH']+os.pathsep+str(REPO/'.tools/ffmpeg'))
    narration=tmp_path/'narration.wav';tone(narration,22050,1,8,300,.12,lambda s: s<2 or 4<=s<6)
    music=tmp_path/'muzică ș $.wav';tone(music)
    sfx=tmp_path/'sfx.wav';tone(sfx,48000,2,.25,2000,.2)
    image=tmp_path/'image.png';Image.new('RGB',(320,240),'#123456').save(image)
    p,m=core.init('mix-fixture',narration,image=image)
    config=dict(enabled=True,tracks=[dict(type='music',path=str(music),start=0,end=8,loop=True,volume_db=-12)],normalization={'enabled':False})
    return p,m,config,music,sfx


def render(audio,config=None):
    p,m,data,*_=audio;m=deepcopy(m);m['audio_mix']=mix.configure(p,m,config or data,p);return mix.render(p,m),m


def values(path,rate=22050):
    return [v for a in mix.pcm(path,rate) for v in a]


def level(v,a,b,freq=1000,rate=22050):
    left=round(a*rate);right=round(b*rate);n=right-left
    sin=sum(v[i]*math.sin(2*math.pi*freq*i/rate) for i in range(left,right))*2/n
    cos=sum(v[i]*math.cos(2*math.pi*freq*i/rate) for i in range(left,right))*2/n
    return math.hypot(sin,cos)


@pytest.mark.parametrize('field,value',[('start',-1),('end',9),('source_start',-1),('source_end',3),('source_end',0),
    ('fade_in',9),('fade_out',-1),('volume_db',float('nan')),('loop','true'),('path','/missing.wav'),('type','narration'),('checksum','bad')])
def test_invalid_track_config(audio,field,value):
    p,m,c,*_=audio;c['tracks'][0][field]=value
    with pytest.raises(ValueError):mix.configure(p,m,c,p)


@pytest.mark.parametrize('config',[dict(enabled='yes'),dict(enabled=True,tracks={}),dict(enabled=True,ducking={'attack_ms':0}),
    dict(enabled=True,normalization={'true_peak_db':1}),dict(enabled=True,unknown=1)])
def test_invalid_mix_config(audio,config):
    p,m,*_=audio
    with pytest.raises(ValueError):mix.configure(p,m,config,p)


def test_corrupt_and_no_audio_input(audio,tmp_path):
    p,m,c,*_=audio;bad=tmp_path/'bad.wav';bad.write_bytes(b'not audio');c['tracks'][0]['path']=str(bad)
    with pytest.raises(ValueError):mix.configure(p,m,c,p)
    c['tracks'][0]['path']=str(tmp_path/'image.png')
    with pytest.raises(ValueError):mix.configure(p,m,c,p)


def test_resampling_duration_gain_and_disabled_identity(audio,tmp_path):
    (out,r),m=render(audio);assert r['verification']['frames']==8*22050
    assert r['verification']['format']['sample_rate']==22050 and r['verification']['format']['channels']==1
    decoded=values(out);assert .025<level(decoded,3,3.5)<.035
    p=audio[0];baseline=core.assemble(p,m,tmp_path/'baseline.wav');original=core.sha(core.checked(p,m['timeline'][0]['source']))
    m['audio_mix']['enabled']=False;off,_=mix.render(p,m)
    assert values(off)==values(baseline) and core.sha(core.checked(p,m['timeline'][0]['source']))==original
    assert mix.render(p,m)[1]['cache_hit']


def test_ducking_measured_not_just_filtergraph(audio):
    p,m,c,*_=audio;c['ducking']=dict(enabled=True,amount_db=12,attack_ms=40,release_ms=250,threshold_db=-40)
    (out,r),_=render(audio,c);v=values(out);voiced=level(v,1,1.5);pause=level(v,3.4,3.9)
    assert 10<20*math.log10(pause/voiced)<13
    assert abs(pause-.12*10**(-12/20))<.003
    # The first attack window has more background than its settled state.
    assert level(v,0,.05)>voiced*1.3
    core.write(core.ROOT/'ducking-proof.json',dict(technical_audio_status='passed',voiced_tone_amplitude=voiced,pause_tone_amplitude=pause,
        measured_duck_db=20*math.log10(pause/voiced),voiced_window=[1,1.5],pause_window=[3.4,3.9],measurement='1000Hz orthogonal projection; narration 300Hz',listening_review='not_listened'))


def test_sfx_sample_placement_and_source_rate(audio):
    p,m,c,music,sfx=audio;c['tracks']=[dict(type='sfx',path=str(sfx),start='00:02.125',duration=.25,volume_db=-6)]
    (out,_),_=render(audio,c);v=values(out);start=mix.samples('00:02.125',22050)
    assert max(map(abs,v[2*22050:start]),default=0)<1e-7
    assert max(map(abs,v[start:start+100]))>.05
    assert max(map(abs,v[start+round(.25*22050)+2:3*22050]),default=0)<1e-7
    assert mix.samples('02:31.200',22050)==3333960
    onset=next(i for i in range(2*22050,3*22050) if abs(v[i])>1e-6)
    core.write(core.ROOT/'sfx-timing-proof.json',dict(technical_audio_status='passed',expected_start_sample=start,measured_first_nonzero_sample=onset,
        sample_error=onset-start,sample_rate=22050,tolerance_samples=2,source_rate=48000,source_channels=2))
    assert 0<=onset-start<=2


def test_loop_noloop_fade_trim(audio):
    p,m,c,*_=audio;c['tracks'][0].update(loop=False,source_start=.5,source_end=1.5,fade_in=.2,fade_out=.2)
    (out,_),_=render(audio,c);v=values(out)
    assert level(v,.01,.04)<level(v,.4,.6)*.3
    assert level(v,.94,.98)<level(v,.4,.6)*.4
    assert level(v,3,3.5)<1e-6
    c['tracks'][0].update(loop=True,fade_in=0,fade_out=0)
    (out,_),_=render(audio,c);looped=values(out);assert level(looped,3.2,3.7)>.02
    assert abs(looped[3*22050]-looped[3*22050-1])<.005


def test_final_normalization_clipping_and_silence(audio,tmp_path):
    p,m,c,music,_=audio;tone(music,amplitude=.8);c['tracks'][0]['volume_db']=24
    c['normalization']={'enabled':True};(out,r),_=render(audio,c)
    assert r['normalization']['before']['peak']>1
    assert abs(r['verification']['loudness']['input_i']+19)<1
    assert r['verification']['loudness']['input_tp']<=-1.9
    c['normalization']={'enabled':False};(out,r),_=render(audio,c)
    assert 'static_peak_attenuation' in r['normalization']['mode'] and r['verification']['peak']<.81
    silence=tmp_path/'silence.wav';tone(silence,22050,1,8,amplitude=0)
    m['timeline'][0]['source']=core.reference(silence,p);m['audio_mix']=mix.configure(p,m,dict(enabled=True,tracks=[]),p)
    out,r=mix.render(p,m);assert r['verification']['peak']==0


def test_split_and_merge_preserve_processed_context_exactly(audio):
    p,m,c,*_=audio;c['ducking']={'enabled':True};c['normalization']={'enabled':True}
    (parent,_),m=render(audio,c);core.write(p,m);baseline=values(parent)
    _,_,plan=derive.split_plan(p,'partition',[[0,3*22050],[3*22050,8*22050]])
    children=derive.apply_split(p,plan,'mixed-child');parts=[]
    for child in children:
        q,cm=core.load(child);out,_=mix.render(q,cm);parts+=values(out)
    assert parts==baseline
    merged=derive.merge(children,'mixed-merged');q,mm=core.load(merged);out,_=mix.render(q,mm)
    assert values(out)==baseline
    assert mm['audio_mix']['segments'][0]['context']['audio_mix']['segments'][0]['context']['audio_mix']['ducking']['enabled']


def test_cache_fingerprint_scene_and_originals_unchanged(audio):
    p,m,c,*_=audio;(out,r),changed=render(audio,c)
    config=core.config(REPO/'media.json');scene_key=video.scene_key(m['scenes'][0],[320,240],config,None,True)
    baseline=dict(timeline=deepcopy(m['timeline']),alignment=deepcopy(m['alignment']),source=core.sha(core.checked(p,m['timeline'][0]['source'])))
    first=mix.fingerprint(p,changed);assert mix.render(p,changed)[1]['cache_hit']
    for k,v in [('volume_db',-20),('start',.1),('fade_in',.1),('loop',False)]:
        data=deepcopy(c);data['tracks'][0][k]=v;other=deepcopy(m);other['audio_mix']=mix.configure(p,other,data,p)
        assert mix.fingerprint(p,other)!=first
        assert video.scene_key(other['scenes'][0],[320,240],config,None,True)==scene_key
    assert dict(timeline=m['timeline'],alignment=m['alignment'],source=core.sha(core.checked(p,m['timeline'][0]['source'])))==baseline


def test_missing_changed_source_and_disabled_bypass(audio):
    p,m,c,music,_=audio;m['audio_mix']=mix.configure(p,m,c,p);music.write_bytes(b'changed corrupt fixture')
    with pytest.raises(ValueError):mix.render(p,m)
    m['audio_mix']['enabled']=False
    _,r=mix.render(p,m);assert r['verification']['frames']==m['frames']


def test_deterministic_fresh_cache(audio,tmp_path):
    p,m,c,*_=audio;m['audio_mix']=mix.configure(p,m,c,p)
    first,_=mix.render(p,m,tmp_path/'cache-one');second,_=mix.render(p,m,tmp_path/'cache-two')
    assert core.sha(first)==core.sha(second)


def test_mono_ambience_and_distinct_merge_settings(audio,tmp_path):
    p,m,c,music,_=audio;ambience=tmp_path/'ambience.wav';tone(ambience,48000,1,2,700,.1)
    c['tracks']=[dict(type='ambience',path=str(ambience),start=2,end=7,loop=False,fade_in=.1,fade_out=.1,volume_db=-10)]
    (_,r),m=render(audio,c);assert r['verification']['frames']==m['frames'];core.write(p,m)
    q=tmp_path/'materials/second/material.json';second=deepcopy(m);second['id']='second';second=mix.absolute(second,p)
    second['audio_mix']['tracks'][0]['volume_db']=-20;core.write(q,second)
    merged=derive.merge([p,q],'distinct-mixes');mp,mm=core.load(merged)
    assert len(mm['audio_mix']['segments'])==2
    assert mm['audio_mix']['segments'][0]['context']['audio_mix']['tracks'][0]['volume_db']==-10
    assert mm['audio_mix']['segments'][1]['context']['audio_mix']['tracks'][0]['volume_db']==-20


def test_failure_preserves_parts_no_publication_and_retry(audio,monkeypatch):
    p,m,c,*_=audio;m['audio_mix']=mix.configure(p,m,c,p);real=mix.normalization
    def fail(raw,part,*args):Path(part).write_bytes(b'incomplete');raise ValueError('fixture interrupted normalization')
    monkeypatch.setattr(mix,'normalization',fail)
    with pytest.raises(ValueError):mix.render(p,m)
    folder=core.ROOT/'work/media/audio-mix'/mix.fingerprint(p,m)
    assert list(folder.rglob('mix.part.wav')) and not (folder/'mix.wav').exists() and not (folder/'receipt.json').exists()
    monkeypatch.setattr(mix,'normalization',real);out,r=mix.render(p,m)
    assert out.is_file() and r['technical_audio_status']=='passed' and list(folder.rglob('mix.part.wav'))


def test_real_ffmpeg_failure_receipt_and_retry(audio,monkeypatch):
    p,m,c,*_=audio;m['audio_mix']=mix.configure(p,m,c,p);real=mix.command
    def invalid_filter(folder,label,args):
        if label=='mix':args=mix.input_args(Path(folder)/'narration.wav')+['-af','rec_intentionally_missing_filter','-f','null','-']
        return real(folder,label,args)
    monkeypatch.setattr(mix,'command',invalid_filter)
    with pytest.raises(ValueError,match='FFmpeg exit'):mix.render(p,m)
    folder=core.ROOT/'work/media/audio-mix'/mix.fingerprint(p,m)
    receipt=next(folder.rglob('mix-*.command.json'));assert core.read(receipt)['returncode']!=0
    assert not (folder/'mix.wav').exists()
    monkeypatch.setattr(mix,'command',real);out,r=mix.render(p,m);assert out.exists()


def test_video_remux_and_render_cache_no_caption_generation(audio,tmp_path,monkeypatch):
    p,m,c,*_=audio;config=core.config(REPO/'media.json');config.update(crf=30,preset='ultrafast')
    baseline=video.render(p,{'custom':[320,240]},config,output_root=tmp_path/'baseline')
    m=core.load(p)[1];m['audio_mix']=mix.configure(p,m,c,p);core.write(p,m)
    def forbidden(*args,**kwargs):raise AssertionError('No subtitle generation on mix-only change')
    monkeypatch.setattr(video,'subtitle_files',forbidden)
    mixed=video.render(p,{'custom':[320,240]},config,output_root=tmp_path/'mixed',resume_run=baseline['run_id'])
    assert mixed['outputs'][0]['video_packets_identical']
    run=core.read(core.ROOT/'work/media/runs'/baseline['run_id']/'run.json')
    assert run['reused_compositions'] and not run.get('rendered_scenes')
    assert baseline['outputs'][0]['verification']['decoded_audio_sha256']!=mixed['outputs'][0]['verification']['decoded_audio_sha256']


def test_initial_render_checks_mixed_aac(audio,tmp_path):
    p,m,c,*_=audio;m['audio_mix']=mix.configure(p,m,c,p);core.write(p,m)
    config=core.config(REPO/'media.json');config.update(crf=30,preset='ultrafast')
    result=video.render(p,{'custom':[320,240]},config,output_root=tmp_path/'initial-mixed')
    report=core.read(Path(result['outputs'][0]['path']).with_suffix('.report.json'))
    assert report['audio_mix']['mux_verification']['full_decode']
    assert report['audio_mix']['mux_verification']['loudness']['input_tp']<=-1
