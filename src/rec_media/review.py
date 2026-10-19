"""Human review of observed CTC units, bound to the exact source/timing revision."""
from copy import deepcopy
from pathlib import Path
from datetime import datetime
import hashlib
import json
import os
import shutil
import uuid

from .core import checked, key, load, now, read, write, sha
from .content import stamp


def alignment_key(m):
    a=m.get('alignment')
    if not a:raise ValueError('Material fără aliniere.')
    return key(dict(timeline=m['timeline'],words=[{k:v for k,v in w.items() if k!='review'} for w in a['words']]))


def bindings(p,m):
    # Verify the files, not merely the checksums recorded in a mutable manifest.
    clips=[]
    for clip in m['timeline']:
        source=checked(p,clip['source'])
        clips.append(dict(sha256=sha(source),start=clip['start'],end=clip['end'],timeline_start=clip['timeline_start']))
    source_files={'original_text':[],'original_audio':[]}
    for source in m.get('sources',[]):
        if source.get('role') in source_files:source_files[source['role']].append(sha(checked(p,source)))
    return dict(alignment_key=alignment_key(m),source_text_sha256=key(dict(text={k:m.get(k,'') for k in ('text_original','text_display','text_spoken')},files=source_files['original_text'])),
                audio_sha256=key(dict(sample_rate=m['sample_rate'],frames=m['frames'],clips=clips,original_files=source_files['original_audio'])))


def report(value,output,media=None):
    p,m=load(value);signature=alignment_key(m);groups={};rate=m['sample_rate']
    threshold=m['alignment'].get('settings',{}).get('confidence_warning',.35)
    for i,w in enumerate(m['alignment']['words']):
        if w.get('confidence',1)>=threshold and not w.get('review'):continue
        segment=w.get('window','manual');item=dict(index=i,word=w['spoken'],start=w['start'],end=w['end'],
            timestamp=stamp(w['start'],rate),confidence=w.get('confidence'),review=w.get('review',{'status':'pending'}))
        groups.setdefault(str(segment),[]).append(item)
    output=Path(output)
    if output.exists() or output.with_suffix('.md').exists():raise ValueError('Raport existent; alege alt nume.')
    rejected=sorted({w['window'] for w in m['alignment']['words'] if w.get('review',{}).get('status')=='rejected' and 'window' in w})
    result=dict(schema_version=2,material=m['id'],created_utc=now(),**bindings(p,m),sample_rate=rate,frames=m['frames'],threshold=threshold,
                total_units=sum(len(v) for v in groups.values()),segments=groups,rerun_segments=rejected,
                intervals=[dict(start=w['start'],end=w['end']) for w in m['alignment']['words']],
                normalizations=m['alignment'].get('normalization',[]),decisions=[],technical_status='passed',listening_status='not_listened',ctc_human_review='pending')
    write(output,result)
    lines=['# Unități CTC de revizuit','',f'Material: {m["id"]}; prag: {threshold}; indici de segment **de la zero**.','']
    for segment,items in groups.items():
        lines.extend([f'## Segment {segment}','','| Index | Timestamp | Cuvânt | Confidence | Review |','|---|---|---|---|---|'])
        for item in items:
            word=item['word'].replace('|',r'\|').replace('\n',' ')
            lines.append(f'| {item["index"]} | {item["timestamp"]} | {word} | {item["confidence"]} | {item["review"]["status"]} |')
        lines.append('')
    output.with_suffix('.md').write_text('\n'.join(lines),encoding='utf-8')
    from .review_ui import generate
    generate(p,m,result,output.with_suffix('.html'),media)
    return result


def validate(value,path):
    p,m=load(value);data=read(path)
    if not isinstance(data,dict):raise ValueError('Fișierul de decizii trebuie să fie un obiect JSON.')
    sidecar=p.parent/'alignment.json'
    if sidecar.exists() and read(sidecar)!=m['alignment']:raise ValueError('Alinierea din material diferă de sidecar; audit necesar înainte de apply.')
    for field,expected in bindings(p,m).items():
        if data.get(field)!=expected:raise ValueError(f'Review pentru altă revizie / hash mismatch: {field}.')
    if not isinstance(data.get('reviewer'),str) or not data['reviewer'].strip():raise ValueError('Specifică reviewer explicit; nu se inventează aprobări umane.')
    try:
        timestamp=datetime.fromisoformat(data['reviewed_utc'].replace('Z','+00:00'))
        if timestamp.tzinfo is None:raise ValueError()
    except (KeyError,TypeError,AttributeError,ValueError):raise ValueError('reviewed_utc cere timestamp ISO cu fus orar.')
    if not isinstance(data.get('decisions'),list) or not data['decisions']:raise ValueError('Lista de decizii este goală.')
    alignment=deepcopy(m['alignment']);seen=set()
    actions={'ACCEPT':('accepted',()),'ADJUST_START':('corrected',('start',)),
             'ADJUST_END':('corrected',('end',)),'ADJUST_BOTH':('corrected',('start','end')),
             'REJECT':('rejected',()),'NEEDS_REVIEW':('needs_review',()),
             'accepted':('accepted',()),'rejected':('rejected',()),'corrected':('corrected',('start','end'))}
    for decision in data['decisions']:
        if not isinstance(decision,dict):raise ValueError('Decizie JSON invalidă.')
        index=decision.get('index');action=decision.get('action',decision.get('status'))
        if type(index) is not int or not 0<=index<len(alignment['words']) or index in seen:raise ValueError('Index invalid/repetat.')
        if not isinstance(action,str) or action not in actions:raise ValueError('Status review invalid.')
        status,fields=actions[action]
        seen.add(index);word=alignment['words'][index]
        previous={k:word[k] for k in ('start','end')}
        if {f for f in ('start','end') if f in decision}!=set(fields):raise ValueError('Câmpurile start/end nu corespund deciziei explicite.')
        for field in fields:
            if type(decision[field]) is not int:raise ValueError('Corecția cere start/end în eșantioane întregi.')
            word[field]=decision[field]
        if not isinstance(decision.get('note',''),str):raise ValueError('Notă invalidă.')
        word['review']=dict(status=status,action=action,reviewer=data['reviewer'].strip(),note=decision.get('note',''),created_utc=data['reviewed_utc'],previous=previous)
    cursor=0
    for word in alignment['words']:
        if not cursor<=word['start']<word['end']<=m['frames']:raise ValueError('Corecția produce suprapunere sau interval invalid.')
        cursor=word['end']
    alignment['low_confidence']=[dict(index=i,spoken=w['spoken'],confidence=w.get('confidence'),start=w['start'],end=w['end']) for i,w in enumerate(alignment['words']) if w.get('confidence',1)<alignment.get('settings',{}).get('confidence_warning',.35)]
    untouched=[i for i in range(len(alignment['words'])) if i not in seen]
    assert all(key(alignment['words'][i])==key(m['alignment']['words'][i]) for i in untouched)
    return p,m,data,alignment,dict(technical_status='passed',validation_only=True,explicit_indices=sorted(seen),untouched_units=len(untouched),
        before_alignment_key=alignment_key(m),after_alignment_key=alignment_key(dict(m,alignment=alignment)),
        before_words_sha256=key(m['alignment']['words']),after_words_sha256=key(alignment['words']),
        units=[dict(index=i,before=m['alignment']['words'][i],after=alignment['words'][i]) for i in sorted(seen)])


def apply(value,path,validate_only=False):
    p,m=load(value);digest=sha(path);folder=p.parent/'alignment-reviews'
    # Resumable two-file publication: accept only the exact before/after bytes.
    for journal in folder.glob('*/journal.json'):
        state=read(journal)
        if state.get('decisions_sha256')!=digest:continue
        evidence=read(journal.parent/'before-after.json');current_bindings=bindings(p,m)
        for field in ('source_text_sha256','audio_sha256'):
            if current_bindings[field]!=evidence['bindings'][field]:raise ValueError(f'Jurnal review: hash mismatch {field}.')
        if current_bindings['alignment_key'] not in (evidence['before_alignment_key'],evidence['after_alignment_key']):raise ValueError('Jurnal pentru altă revizie a alinierii.')
        for target in state['files']:
            f=Path(target['path']);current=sha(f) if f.exists() else None
            if current not in (target['before_sha256'],target['after_sha256']):raise ValueError('Jurnal review incompatibil cu fișierele actuale.')
        if validate_only:return dict(technical_status='passed',already_applied=state['phase']=='complete',journal=str(journal))
        for target in state['files']:
            f=Path(target['path'])
            if not f.exists() or sha(f)!=target['after_sha256']:
                write(f,read(journal.parent/target['after']))
        state.update(phase='complete',completed_utc=now());write(journal,state)
        return dict(technical_status='passed',already_applied=True,journal=str(journal),report=str(journal.parent/'before-after.json'))
    p,m,data,alignment,result=validate(value,path)
    if validate_only:return result
    before=deepcopy(m)
    alignment['status']='manually_reviewed_partial';m['alignment']=alignment;m['alignment_status']='manually_reviewed_partial'
    if len(m.get('text_units',[]))==len(alignment['words']):
        for i in result['explicit_indices']:
            m['text_units'][i].update(start=alignment['words'][i]['start'],end=alignment['words'][i]['end'])
    m['history'].append(dict(action='alignment_review',created_utc=now(),reviewer=data['reviewer'],decisions=data['decisions'],previous_alignment_key=data['alignment_key']))
    audit=folder/uuid.uuid4().hex;audit.mkdir(parents=True)
    shutil.copy2(path,audit/'decisions.json');files=[]
    for target,after in [(p.parent/'alignment.json',alignment),(p,m)]:
        backup=audit/('before-'+target.name);after_path=audit/('after-'+target.name)
        exists=target.exists()
        if exists:shutil.copy2(target,backup)
        else:write(backup,before['alignment'])
        write(after_path,after)
        for f in (backup,after_path):
            with f.open('rb') as h:os.fsync(h.fileno())
        files.append(dict(path=str(target.resolve()),before_sha256=sha(backup) if exists else None,after_sha256=sha(after_path),after=after_path.name))
    result.update(utc=now(),validation_only=False,reviewer=data['reviewer'],reviewed_utc=data['reviewed_utc'],bindings=bindings(p,before),ctc_human_review='explicit_decisions_only')
    write(audit/'before-after.json',result)
    state=dict(phase='prepared',created_utc=now(),decisions_sha256=digest,files=files);write(audit/'journal.json',state)
    for target in files:write(target['path'],read(audit/target['after']))
    state.update(phase='complete',completed_utc=now());write(audit/'journal.json',state)
    return dict(technical_status='passed',decisions_applied=len(result['explicit_indices']),alignment_status=m['alignment_status'],journal=str(audit/'journal.json'),report=str(audit/'before-after.json'))
