"""Human review of observed CTC units, bound to the exact source/timing revision."""
from copy import deepcopy
from pathlib import Path

from .core import key, load, now, read, write
from .content import stamp


def alignment_key(m):
    a=m.get('alignment')
    if not a:raise ValueError('Material fără aliniere.')
    return key(dict(timeline=m['timeline'],words=[{k:v for k,v in w.items() if k!='review'} for w in a['words']]))


def report(value,output):
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
    result=dict(material=m['id'],created_utc=now(),alignment_key=signature,sample_rate=rate,threshold=threshold,
                total_units=sum(len(v) for v in groups.values()),segments=groups,rerun_segments=rejected,
                decisions=[],technical_status='passed',listening_status='not_listened')
    write(output,result)
    lines=['# Unități CTC de revizuit','',f'Material: {m["id"]}; prag: {threshold}; indici de segment **de la zero**.','']
    for segment,items in groups.items():
        lines.extend([f'## Segment {segment}','','| Index | Timestamp | Cuvânt | Confidence | Review |','|---|---|---|---|---|'])
        for item in items:
            word=item['word'].replace('|',r'\|').replace('\n',' ')
            lines.append(f'| {item["index"]} | {item["timestamp"]} | {word} | {item["confidence"]} | {item["review"]["status"]} |')
        lines.append('')
    output.with_suffix('.md').write_text('\n'.join(lines),encoding='utf-8')
    return result


def apply(value,path):
    p,m=load(value);data=read(path)
    if data['alignment_key']!=alignment_key(m):raise ValueError('Review pentru altă revizie a alinierii.')
    if not isinstance(data.get('reviewer'),str) or not data['reviewer'].strip():raise ValueError('Specifică reviewer explicit; nu se inventează aprobări umane.')
    alignment=deepcopy(m['alignment']);seen=set()
    for decision in data['decisions']:
        index=decision['index'];status=decision['status']
        if type(index) is not int or not 0<=index<len(alignment['words']) or index in seen:raise ValueError('Index invalid/repetat.')
        if status not in ('accepted','rejected','corrected'):raise ValueError('Status review invalid.')
        seen.add(index);word=alignment['words'][index]
        previous={k:word[k] for k in ('start','end')}
        if status=='corrected':
            for field in ('start','end'):
                if type(decision.get(field)) is not int:raise ValueError('Corecția cere start/end în eșantioane.')
                word[field]=decision[field]
        elif 'start' in decision or 'end' in decision:raise ValueError('Timpii se schimbă numai cu status corrected.')
        word['review']=dict(status=status,reviewer=data['reviewer'],note=decision.get('note',''),created_utc=now(),previous=previous)
    cursor=0
    for word in alignment['words']:
        if not cursor<=word['start']<word['end']<=m['frames']:raise ValueError('Corecția produce suprapunere sau interval invalid.')
        cursor=word['end']
    alignment['low_confidence']=[dict(index=i,spoken=w['spoken'],confidence=w['confidence'],start=w['start'],end=w['end']) for i,w in enumerate(alignment['words']) if w.get('confidence',1)<alignment.get('settings',{}).get('confidence_warning',.35)]
    alignment['status']='manually_reviewed_partial';m['alignment']=alignment;m['alignment_status']='manually_reviewed_partial'
    m['text_units']=[dict(start=w['start'],end=w['end'],spoken=w['spoken'],display=w.get('display',w['spoken']),timing=w.get('timing','word_import')) for w in alignment['words']]
    m['history'].append(dict(action='alignment_review',created_utc=now(),reviewer=data['reviewer'],decisions=data['decisions'],previous_alignment_key=data['alignment_key']))
    write(p.parent/'alignment.json',alignment);write(p,m)
    return dict(technical_status='passed',decisions_applied=len(seen),alignment_status=m['alignment_status'])
