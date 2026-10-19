"""New timelines are derived; no production voice/model/alignment is written."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import math
import subprocess
import pytest
from test_audio_mix import audio,tone,values,REPO
from rec_media import core,audio_mix as mix,audio_timeline as timing,compilation,derive,video


def pcm32(path):
    return subprocess.run([core.tool('ffmpeg'),'-nostdin','-v','error',*mix.input_args(path),'-map','0:a:0','-ac','1','-f','s32le','pipe:1'],capture_output=True,check=True).stdout


def compile_one(audio,tmp_path,settings=None,name='compiled',materials=None):
    p,m,*_=audio;config=tmp_path/'composition.json';core.write(config,settings or {'normalization':{'enabled':False}})
    path=compilation.create(materials or [p],name,core.read(config),config);q,cm=core.load(path)
    out,report=mix.render(q,cm);return q,cm,out,report


@pytest.mark.parametrize('rate,channels,codec',[(22050,1,'pcm_s16le'),(44100,2,'flac'),(48000,2,'pcm_f32le')])
def test_narration_import_formats_conversion(audio,tmp_path,rate,channels,codec):
    source=tmp_path/'input.wav';tone(source,rate,channels,1.001,700,.1)
    encoded=tmp_path/('encoded.flac' if codec=='flac' else 'encoded.wav')
    core.ff(['-i',source,'-c:a',codec,encoded]);before=(core.sha(encoded),encoded.stat().st_mtime_ns)
    p,m=core.init('converted',encoded,sample_rate=22050)
    actual=core.checked(p,m['timeline'][0]['source']);expected=timing.scale(round(1.001*rate),rate,22050)
    assert m['frames']==expected and m['sample_rate']==22050
    assert core.probe(actual)['streams'][0]['channels']==1
    assert (core.sha(encoded),encoded.stat().st_mtime_ns)==before
    a,_=timing.convert(encoded,22050,cache=tmp_path/'fresh-one');b,_=timing.convert(encoded,22050,cache=tmp_path/'fresh-two')
    assert core.sha(a)==core.sha(b)


def test_convert_material_no_original_mutation(audio,tmp_path):
    p,m,*_=audio;before=p.read_bytes();source=core.checked(p,m['timeline'][0]['source']);sha=core.sha(source)
    q=compilation.convert_material(p,'rate48000',48000);_,cm=core.load(q)
    assert cm['frames']==384000 and cm['sample_rate']==48000
    assert p.read_bytes()==before and core.sha(source)==sha


@pytest.mark.parametrize('setting',[{'pause_before':0},{'pause_after':-1},{'pause_between':0},{'intro':{'duration':0}},
    {'outro':{'duration':-.1}},{'sample_rate':True},{'visual':{'mode':'arbitrary'}}])
def test_invalid_explicit_slots(audio,tmp_path,setting):
    p,m,*_=audio
    with pytest.raises(ValueError):compilation.create([p,p],'invalid',setting,tmp_path/'config.json')
    assert not (core.ROOT/'materials/invalid/material.json').exists()


def test_pauses_intro_outro_exact_pcm_positions(audio,tmp_path):
    p,m,*_=audio
    settings=dict(intro={'duration':.2},pause_before=.1,pause_between=.25,pause_after=.15,outro={'duration':.3},normalization={'enabled':False})
    q,cm,out,r=compile_one(audio,tmp_path,settings,materials=[p,p]);raw=pcm32(out)
    source=core.assemble(p,m,tmp_path/'source.wav');original=pcm32(source)
    events=cm['compilation']['events'];assert cm['frames']==2*m['frames']+mix.samples(1,22050)
    for e in events:
        block=raw[4*e['start']:4*e['end']]
        assert block==(original if e['kind']=='narration' else b'\0'*((e['end']-e['start'])*4))
    core.write(tmp_path/'positions-proof.json',dict(events=events,expected_samples=cm['frames'],actual_samples=len(raw)//4))


def test_intro_outro_reuse_mixer_provenance(audio,tmp_path):
    p,m,c,music,sfx=audio
    settings=dict(intro=dict(duration=.4,audio=dict(type='music',path=str(music),volume_db=-12,source_start=.2,source_end=.8,fade_in=.03,fade_out=.04,creator='fixture',license='technical_fixture')),
        outro=dict(duration=.3,audio=dict(type='sfx',path=str(sfx),volume_db=-9,fade_in=.01,fade_out=.02)),normalization={'enabled':False})
    q,cm,out,r=compile_one(audio,tmp_path,settings);v=values(out)
    assert max(map(abs,v[:mix.samples(.4,22050)]))>.01
    assert max(map(abs,v[-mix.samples(.3,22050):]))>.01
    assert cm['audio_mix']['segments'][0]['context']['audio_mix']['tracks'][0]['source']['creator']=='fixture'
    assert cm['compilation']['events'][1]['start']==8820 and cm['compilation']['events'][-1]['start']==185220


def test_normalized_inserted_pauses_are_exact_zero(audio,tmp_path):
    q,cm,out,r=compile_one(audio,tmp_path,dict(pause_before=.25,pause_after=.15,normalization={'enabled':True}))
    raw=pcm32(out)
    for a,b in cm['audio_mix']['silence_intervals']:assert raw[a*4:b*4]==b'\0'*((b-a)*4)
    assert abs(r['verification']['loudness']['input_i']+19)<=1


def test_many_segments_global_rational_rounding_no_drift(audio,tmp_path):
    short=tmp_path/'short.wav';tone(short,44100,2,111/44100,700,.1)
    p,m=core.init('short',short);config=tmp_path/'config.json';core.write(config,{})
    settings=dict(sample_rate=22050,normalization={'enabled':False})
    q=compilation.create([p]*100,'hundred',settings,config);q,cm=core.load(q);out,r=mix.render(q,cm)
    expected=timing.scale(111*100,44100,22050);actual=len(pcm32(out))//4
    assert expected==actual==cm['frames']==5550
    assert sum(e['rounding_adjustment'] for e in cm['compilation']['events'])==-50
    core.write(tmp_path/'drift-proof.json',dict(segments=100,expected_samples=expected,actual_samples=actual,naive_independent_rounding=100*timing.scale(111,44100,22050)))


def test_global_once_not_independent_normalization(audio,tmp_path,monkeypatch):
    p,m,*_=audio;quiet=tmp_path/'quiet.wav';loud=tmp_path/'loud.wav'
    tone(quiet,22050,1,4,400,.02);tone(loud,22050,1,4,400,.2)
    qa,ma=core.init('quiet',quiet);qb,mb=core.init('loud',loud)
    # Parent recipes deliberately request normalization; compilation must bypass
    # those final passes and normalize the entire raw mix exactly once.
    for doc,mat in [(qa,ma),(qb,mb)]:mat['audio_mix']=mix.configure(doc,mat,dict(enabled=True,tracks=[]),doc);core.write(doc,mat)
    real=mix.normalization;calls=[]
    def counted(*args,**kw):calls.append(args[3]);return real(*args,**kw)
    monkeypatch.setattr(mix,'normalization',counted)
    q,cm,out,report=compile_one(audio,tmp_path,{'normalization':{'enabled':True}},materials=[qa,qb])
    assert len(calls)==1 and calls[0]==8*22050
    global_measured=report['verification']['loudness'];assert abs(global_measured['input_i']+19)<=1 and global_measured['input_tp']<=-1.9
    a,_=mix.render(qa,ma);b,_=mix.render(qb,mb)
    separately=mix.measure(a,tmp_path/'measure-a',22050)['loudness'],mix.measure(b,tmp_path/'measure-b',22050)['loudness']
    v=values(out)
    def rms(a,b):return math.sqrt(sum(x*x for x in v[a*22050:b*22050])/((b-a)*22050))
    relative=20*math.log10(rms(5,7)/rms(1,3));assert relative>5
    core.write(tmp_path/'normalization-proof.json',dict(global_measurements=global_measured,independent_measurements=separately,global_relative_level_db=relative,global_final_passes=1,frames=len(v)))


def test_compilation_split_merge_pcm_exact_and_boundary_detection(audio,tmp_path):
    q,cm,out,r=compile_one(audio,tmp_path,{'normalization':{'enabled':True}})
    _,_,plan=derive.split_plan(q,'partition',[[0,3*22050],[3*22050,8*22050]])
    children=derive.apply_split(q,plan,'pieces');merged=derive.merge(children,'restored');mp,mm=core.load(merged)
    restored,_=mix.render(mp,mm);assert pcm32(out)==pcm32(restored)
    points=timing.boundaries(restored,[3*22050],22050);assert not points['boundaries'][0]['large_step']
    # Deliberate sign step must be reported, never silently faded.
    import struct,wave
    step=tmp_path/'step.wav'
    with wave.open(str(step),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(22050);f.writeframes(struct.pack('<h',20000)*100+struct.pack('<h',-20000)*100)
    result=timing.boundaries(step,[100],22050);assert result['boundaries'][0]['step']>1 and result['status']=='needs_listening' and not result['fade_applied']


def test_settings_invalidate_only_derived_timeline(audio,tmp_path):
    p,m,*_=audio;source=core.checked(p,m['timeline'][0]['source']);before=(p.read_bytes(),core.sha(source),source.stat().st_mtime_ns)
    keys=[]
    for i,settings in enumerate([{},dict(pause_before=.1),dict(intro={'duration':.2}),dict(outro={'duration':.2}),dict(normalization={'enabled':False})]):
        path=compilation.create([p],f'comp-{i}',settings,tmp_path/'cfg.json');doc,mat=core.load(path);keys.append(mix.fingerprint(doc,mat))
    assert len(set(keys))==5
    assert (p.read_bytes(),core.sha(source),source.stat().st_mtime_ns)==before


def test_atomic_conversion_failure_retry(audio,tmp_path,monkeypatch):
    source=tmp_path/'44100.wav';tone(source,44100,2,1)
    real=mix.command
    def fail(folder,label,args):
        if label=='convert':return real(folder,label,mix.input_args(source)+['-af','rec_missing_filter','-f','null','-'])
        return real(folder,label,args)
    monkeypatch.setattr(mix,'command',fail)
    with pytest.raises(ValueError):timing.convert(source,22050)
    assert not list((core.ROOT/'work/media/narration-conversion').glob('*/audio.wav'))
    monkeypatch.setattr(mix,'command',real);out,r=timing.convert(source,22050);assert r['frames']==22050


def test_compilation_mp4_existing_picture_no_scene_subtitle_generation(audio,tmp_path,monkeypatch):
    p,m,*_=audio;c=core.config(REPO/'media.json');c.update(preset='ultrafast',crf=30)
    source=video.render(p,{'custom':[320,240]},c,output_root=tmp_path/'baseline')['outputs'][0]['path']
    q,cm,out,r=compile_one(audio,tmp_path,dict(intro={'duration':.2},pause_after=.1,outro={'duration':.2},normalization={'enabled':True}))
    def forbidden(*args,**kw):raise AssertionError('Scene/subtitle generator must not run')
    monkeypatch.setattr(video,'subtitle_files',forbidden)
    result=compilation.video(q,{m['id']:source},tmp_path/'compilation.mp4',tmp_path/'videos.json',[320,240],30)
    assert result['verification']['full_decode'] and not result['scene_generation'] and not result['subtitle_generation']
    assert result['planned_video_frames']==255
