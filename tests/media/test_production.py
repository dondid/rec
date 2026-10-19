from pathlib import Path
import json
import os
import subprocess
import sys

import pytest

from rec_media import core, text_parts, review, recovery, workflow

REPO=core.ROOT


def test_text_partition_exact_unicode_bytes_and_no_word_cuts(tmp_path):
    source=tmp_path/'original.txt';raw=b'\xef\xbb\xbf'+('Ștefan vine. Îl așteptăm!\r\n\r\nAlt capitol.\r\n').encode('utf-8');source.write_bytes(raw)
    result=text_parts.split(source,tmp_path/'parts',parts=3)
    text=raw.decode('utf-8-sig')
    for part in result['parts']:
        assert (tmp_path/'parts'/part['path']).read_bytes()==raw[part['byte_start']:part['byte_end']]
        assert part['end']==len(text) or text[part['end']-1].isspace()
    text_parts.merge(tmp_path/'parts/text-parts.json',tmp_path/'joined.txt')
    assert (tmp_path/'joined.txt').read_bytes()==raw and source.read_bytes()==raw
    (tmp_path/'parts/part-001.txt').write_text('Modificat')
    with pytest.raises(ValueError,match='modificată'):text_parts.merge(tmp_path/'parts/text-parts.json',tmp_path/'bad.txt')


def test_all_text_methods_and_manual_guards(tmp_path):
    source=tmp_path/'text.txt';source.write_text('# Capitolul 1\nAna vine. Ea citește.\n\n# Capitolul 2\nIon pleacă.\n')
    for name,kwargs in [('duration',dict(target=4)),('chapters',dict(chapters=True)),('delimiter',dict(delimiter='# Capitolul')),('semantic',dict(semantic=True))]:
        result=text_parts.split(source,tmp_path/name,**kwargs)
        assert ''.join((tmp_path/name/p['path']).read_text() for p in result['parts'])==source.read_text()
    ranges=tmp_path/'ranges.json';core.write(ranges,{'ranges':[[0,3],[3,len(source.read_text())]]})
    with pytest.raises(ValueError,match='cuvânt'):text_parts.split(source,tmp_path/'manual-bad',manual=ranges)
    core.write(ranges,{'ranges':[[0,2],[2,len(source.read_text())]]})
    assert text_parts.split(source,tmp_path/'manual',manual=ranges)['method']=='manual'
    with pytest.raises(ValueError,match='puține'):text_parts.split(source,tmp_path/'impossible',parts=100)
    with pytest.raises(ValueError):text_parts.split(source,tmp_path/'nan',target=float('nan'))


def test_review_stale_rejected_and_corrected(tmp_path,monkeypatch):
    monkeypatch.setattr(core,'ROOT',tmp_path)
    m=core.base('review',100,500,'Ana vine.')
    audio=tmp_path/'source.wav';audio.write_bytes(b'synthetic hash-only review fixture')
    m['timeline']=[dict(start=0,end=500,timeline_start=0,source={'path':str(audio),'sha256':core.sha(audio)})]
    m['alignment']=dict(audio_timeline_hash=core.key(m['timeline']),words=[dict(spoken='Ana',start=0,end=100,confidence=.1,window=0),dict(spoken='vine.',start=200,end=400,confidence=.9,window=1)])
    p=tmp_path/'materials/review/material.json';core.write(p,m)
    report=review.report(p,tmp_path/'review.json');assert report['total_units']==1 and report['segments']['0'][0]['timestamp']=='00:00:00,000'
    decisions=tmp_path/'decisions.json';core.write(decisions,dict(report,reviewer='synthetic-test-only',reviewed_utc=core.now(),decisions=[dict(index=0,status='rejected')]))
    review.apply(p,decisions)
    from rec_media.content import valid_words
    with pytest.raises(ValueError,match='rejected'):valid_words(core.load(p)[1])
    core.write(decisions,dict(report,reviewer='synthetic-test-only',reviewed_utc=core.now(),decisions=[dict(index=0,status='corrected',start=10,end=110)]))
    review.apply(p,decisions);m=core.load(p)[1]
    assert valid_words(m)[0]['confidence']==.1 and m['alignment']['low_confidence'][0]['start']==10
    assert review.apply(p,decisions)['already_applied']


def test_recovery_atomic_failure_and_corruption(tmp_path,monkeypatch):
    import wave
    audio=tmp_path/'source.wav'
    with wave.open(str(audio),'wb') as f:
        f.setnchannels(1);f.setsampwidth(4);f.setframerate(22050);f.writeframes(b'\0'*22050*4)
    document=tmp_path/'material.json';m=core.base('recovery',22050,22050)
    m['timeline']=[dict(start=0,end=22050,timeline_start=0,source=core.reference(audio,document))]
    monkeypatch.setenv('PATH',os.environ['PATH']+os.pathsep+str(REPO/'.tools/ffmpeg'))
    before=core.sha(audio);real_assemble=recovery.assemble
    def interrupt(*args):
        real_assemble(*args);raise KeyboardInterrupt('controlled fixture interruption after master')
    monkeypatch.setattr(recovery,'assemble',interrupt)
    with pytest.raises(KeyboardInterrupt):recovery.prepare_analysis(document,m,tmp_path/'work')
    assert not (tmp_path/'work/analysis.wav').exists()
    monkeypatch.setattr(recovery,'assemble',real_assemble)
    pcm,receipt=recovery.prepare_analysis(document,m,tmp_path/'work');digest=core.sha(pcm)
    assert not receipt['reused'] and recovery.prepare_analysis(document,m,tmp_path/'work')[1]['reused']
    pcm.write_bytes(b'corrupt')
    assert not recovery.prepare_analysis(document,m,tmp_path/'work')[1]['reused']
    assert core.sha(pcm)==digest and core.sha(audio)==before


def test_workflow_resume_failure_and_output_corruption(tmp_path,monkeypatch):
    root=tmp_path/'project';root.mkdir();(root/'src/rec_media').mkdir(parents=True);(root/'src/rec_tts').mkdir(parents=True)
    wrapper=root/'tts';wrapper.write_text('#!/bin/sh\nexec /usr/bin/python3 -c \'import pathlib,sys; pathlib.Path(sys.argv[1]).write_text("ok")\' "$2"\n');wrapper.chmod(0o755)
    monkeypatch.setattr(workflow,'ROOT',root)
    plan=tmp_path/'plan.json';source=tmp_path/'source.txt';source.write_text('input')
    core.write(plan,{'steps':[dict(id='prepare',tool='tts',args=['prepare','artifact.txt'],inputs=['source.txt'],outputs=['artifact.txt'])]})
    result=workflow.run(plan);assert result['technical_status']=='passed'
    assert workflow.run(plan)['steps'][0]['resumed']
    source.write_text('changed');assert not workflow.run(plan)['steps'][0]['resumed']
    (tmp_path/'artifact.txt').write_text('corrupt');assert not workflow.run(plan)['steps'][0]['resumed']
    assert workflow.run(plan,disable=['prepare'])['steps'][0]['status']=='disabled'
    core.write(plan,{'steps':[dict(id='prepare',tool='tts',args=['fetch-model'],outputs=['artifact.txt'])]})
    with pytest.raises(ValueError,match='instalări'):workflow.run(plan)


def test_profiles_aliases_and_approved_titles(tmp_path,monkeypatch):
    from rec_media import content
    c=core.config(REPO/'media.json');assert core.profiles('youtube-landscape,shorts-portrait',c)=={'youtube-landscape':[1920,1080],'shorts-portrait':[1080,1920]}
    monkeypatch.setattr(core,'ROOT',tmp_path)
    m=core.base('title',100,500,'O propoziție destul de lungă pentru titlu. A doua propoziție oferă context.')
    m['timeline']=[dict(start=0,end=500,timeline_start=0,source={})]
    p=tmp_path/'materials/title/material.json';core.write(p,m)
    selected=content.titles(p,c,manual='Aprobat de utilizator',approve=True)['selected']
    state=content.titles(p,c)
    assert state['selected']==selected and state['locked'] and len(state['candidates'])>=2
    with pytest.raises(ValueError,match='blocat'):content.titles(p,c,manual='Înlocuire')


def test_workflow_selected_scope_and_failed_retry_keep_evidence(tmp_path,monkeypatch):
    root=tmp_path/'project';root.mkdir()
    (root/'src/rec_media').mkdir(parents=True);(root/'src/rec_tts').mkdir(parents=True)
    wrapper=root/'tts'
    wrapper.write_text('#!/bin/sh\nprintf ok > "$2"\n');wrapper.chmod(0o755)
    monkeypatch.setattr(workflow,'ROOT',root)
    plan=tmp_path/'plan.json'
    steps=[dict(id=name,tool='tts',args=['prepare',name+'.txt'],outputs=[name+'.txt']) for name in ['first','second']]
    core.write(plan,dict(steps=steps))
    selected=workflow.run(plan,only=['first'])
    assert selected['technical_status']=='passed' and selected['workflow_status']=='partial'
    assert selected['incomplete']==['second']
    assert core.read(selected['state'])['phase']=='partial'
    complete=workflow.run(plan)
    assert complete['workflow_status']=='complete' and complete['steps'][0]['resumed']
    success=core.read(complete['state'])['steps']['first']
    wrapper.write_text('#!/bin/sh\nexit 1\n')
    failed=workflow.run(plan,only=['first'],rerun=['first'])
    assert failed['technical_status']=='failed'
    record=core.read(failed['state'])['steps']['first']
    assert record['status']=='failed' and record['previous_success']==success
    assert all(core.sha(path)==digest for path,digest in record['previous_success']['artifacts'].items())


def test_optional_image_plan_never_executes_or_downloads(tmp_path):
    from rec_media.backends import image_plan
    request=tmp_path/'request.json'
    job=dict(backend='stable-diffusion.cpp',prompt='Forme geometrice',seed=42,width=512,height=512)
    core.write(request,job)
    blocked=image_plan(request,tmp_path/'blocked.json')
    assert blocked['technical_status']=='blocked' and blocked['execution_status']=='not_executed'
    assert len(blocked['blockers'])==2
    executable=tmp_path/'sd-cli';executable.write_text('#!/bin/sh\nexit 99\n');executable.chmod(0o755)
    model=tmp_path/'model.bin';model.write_bytes(b'synthetic identity fixture, not model weights')
    for name,path in [('executable',executable),('model',model)]:
        job[name]=dict(path=path.name,sha256=core.sha(path),revision='synthetic-test',license='fixture')
    core.write(request,job)
    planned=image_plan(request,tmp_path/'planned.json')
    assert planned['technical_status']=='planned' and planned['execution_status']=='not_executed'
    assert not planned['blockers'] and planned['approval_status']=='pending'
    model.write_bytes(b'changed')
    with pytest.raises(ValueError,match='hash diferit'):image_plan(request,tmp_path/'changed.json')
