"""CTC graph tests use constructed emissions, never pretend to be listening tests."""
import json
from pathlib import Path
import subprocess

import numpy as np
import pytest

from rec_media import alignment, content, core


def test_ctc_repeated_letters_require_blank():
    # a, blank, a, b, blank: the two a labels must not collapse into one.
    probabilities=np.full((5,3),.001,dtype=np.float32)
    probabilities[np.arange(5),[1,0,1,2,0]]=.998
    frames=alignment.viterbi(np.log(probabilities),[1,1,2],0)
    assert frames==[[0],[2],[3]]
    with pytest.raises(ValueError,match='puține'):
        alignment.viterbi(np.log(probabilities[:2]),[1,1,2],0)


def test_ctc_uses_acoustic_positions_not_uniform_duration():
    probabilities=np.full((12,3),.001,dtype=np.float32)
    probabilities[:,0]=.998
    probabilities[2:4]=[.001,.998,.001]
    probabilities[9:11]=[.001,.001,.998]
    assert alignment.viterbi(np.log(probabilities),[1,2],0)==[[2,3],[9,10]]


def test_alignment_key_invalidates_relevant_changes():
    m=dict(timeline=[{'source':{'sha256':'audio-a'}}],text_spoken='Text.',text_display='Text.')
    args=[m,[{'start':0,'end':10,'spoken':'Text.'}],{'revision':'model-a'},{'rate':16000}]
    before=alignment.request_key(*args)
    for field,value in [('text_spoken','Alt text.'),('text_display','ALT text.'),('timeline',[{'source':{'sha256':'audio-b'}}])]:
        changed=dict(m,**{field:value})
        assert alignment.request_key(changed,*args[1:])!=before
    assert alignment.request_key(m,args[1],{'revision':'model-b'},args[3])!=before
    assert alignment.request_key(*args[:3],{'rate':8000})!=before


def test_normalization_keeps_original_display_and_no_century_inference():
    python=core.ROOT/'.venv-align/bin/python'
    if not python.exists():pytest.skip('Explicit alignment environment not installed')
    code="""
import json
from rec_media.alignment import targets
vocab={c:i for i,c in enumerate('abcdefghijklmnopqrstuvwxyzăâîșț|')}
words,ids,owners,notes=targets("În 1967, SRI avea 500.000. Din '89 — PSD.",vocab)
assert ' '.join(w['spoken'] for w in words)=="În 1967, SRI avea 500.000. Din '89 — PSD."
assert all(w['display']==w['spoken'] for w in words)
assert words[1]['alignment_target']=='o mie nouă sute șaizeci și șapte'
assert words[4]['alignment_target']=='cinci sute de mii'
assert words[6]['alignment_target']=='optzeci și nouă'
assert 'nouăsprezece' not in words[6]['alignment_target']
assert len(ids)==len(owners)
print(json.dumps(notes))
"""
    result=subprocess.run([str(python),'-c',code],env={**__import__('os').environ,'PYTHONPATH':str(core.ROOT/'src')},capture_output=True,text=True)
    assert result.returncode==0,result.stderr


def test_long_audio_requires_real_anchors():
    m=dict(history=[],frames=22050*100,sample_rate=22050,text_spoken='Text.')
    with pytest.raises(ValueError,match='ancore'):
        alignment.windows(Path('/tmp/material.json'),m)


def test_model_corruption_detected(tmp_path):
    names=['model.safetensors','config.json','vocab.json','preprocessor_config.json']
    files={}
    for name in names:
        p=tmp_path/name;p.write_bytes(b'valid fixture')
        files[name]={'bytes':p.stat().st_size,'sha256':core.sha(p)}
    core.write(tmp_path/'model.lock.json',dict(files=files))
    alignment.model_identity(tmp_path)
    (tmp_path/'model.safetensors').write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='corupt'):
        alignment.model_identity(tmp_path)


def test_derived_diagnostics_use_local_word_indices():
    from rec_media.derive import local_alignment
    parent={'request':'parent-key','settings':{'confidence_warning':.35},
            'low_confidence':[{'index':99,'start':9000,'end':9500}],
            'normalization':[{'token':'1967','target':'year'},{'token':'PSD','target':'psd'}]}
    words=[{'spoken':'PSD','start':200,'end':500,'confidence':.1}]
    result=local_alignment(parent,words,[{'timeline_start':0}])
    assert result['low_confidence']==[dict(index=0,spoken='PSD',confidence=.1,start=200,end=500)]
    assert result['normalization']==[{'token':'PSD','target':'psd'}]
    assert result['parent_alignment_request']=='parent-key' and 'request' not in result
