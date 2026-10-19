"""Frame-exact partition/extract/merge; all products remain normal materials."""
from copy import deepcopy
from pathlib import Path
import math
import re
from .core import ROOT,base,checked,key,load,new_path,now,reference,resolve,write


def local_alignment(metadata,words,timeline):
    """Keep diagnostics in the derived timeline, rather than copying parent indices."""
    result=deepcopy(metadata)
    if 'request' in result:result['parent_alignment_request']=result.pop('request')
    result.update(words=words,audio_timeline_hash=key(timeline),partial=False)
    if any('confidence' in w for w in words):
        threshold=result.get('settings',{}).get('confidence_warning',.35)
        result['low_confidence']=[dict(index=i,spoken=w['spoken'],confidence=w['confidence'],start=w['start'],end=w['end']) for i,w in enumerate(words) if w.get('confidence',1)<threshold]
    relevant={token for w in words for token in w['spoken'].split()}
    if 'normalization' in result:result['normalization']=[n for n in result['normalization'] if n['token'] in relevant]
    return result


def rebase_refs(value,old,new):
    if isinstance(value,dict):
        out={k:rebase_refs(v,old,new) for k,v in value.items()}
        if 'path' in value and 'sha256' in value:out['path']=reference(resolve(old,value['path']),new)['path']
        return out
    if isinstance(value,list):return [rebase_refs(v,old,new) for v in value]
    return value


def map_scene_text(material):
    """Rebase editorial anchors from known aligned words, without new timings."""
    words=(material.get('alignment') or {}).get('words',[])
    if not words:return
    text=material['text_spoken'];tokens=list(re.finditer(r'\S+',text));cursor=0;mapped=[]
    for word in words:
        pieces=word['spoken'].split();end=cursor+len(pieces)
        if not pieces or [t.group() for t in tokens[cursor:end]]!=pieces:
            raise ValueError('Cuvinte aliniate diferite de text la maparea scenelor.')
        mapped.append((word['start'],word['end'],tokens[cursor].start(),tokens[end-1].end()));cursor=end
    if cursor!=len(tokens):raise ValueError('Text neacoperit la maparea scenelor.')
    for scene in material['scenes']:
        covered=[w for w in mapped if w[0]<scene['end'] and scene['start']<w[1]]
        old=dict(anchor=scene.get('anchor'),text_range=scene.get('text_range'))
        if covered:
            start,end=covered[0][2],covered[-1][3]
            anchor=scene.get('anchor','');position=text.find(anchor,start,end) if anchor else -1
            if position>=0:
                anchor_range=[position,position+len(anchor)];status='literal_anchor_in_aligned_scene'
            else:
                anchor=text[start:end];anchor_range=[start,end];status='derived_from_known_aligned_words'
        else:
            anchor='';anchor_range=None;status='no_aligned_words_in_scene'
        if old!=dict(anchor=anchor,text_range=anchor_range):
            scene.setdefault('text_mapping_history',[]).append(old)
            scene['text_mapping_status']=status
        scene.update(anchor=anchor,text_range=anchor_range)
        scene.setdefault('text_mapping_status',status)


def split_plan(value,mode='partition',intervals=None,parts=None,target=None,maximum=None):
    p,m=load(value);frames=m['frames'];safe={0,frames}
    maximum_frames=None
    if maximum is not None:
        if type(maximum) not in (int,float) or not math.isfinite(maximum) or maximum<=0:
            raise ValueError('Durată maximă invalidă.')
        maximum_frames=math.floor(maximum*m['sample_rate'])
        if maximum_frames<1:raise ValueError('Durata maximă trebuie să includă cel puțin un eșantion.')
    display_intervals={}
    if m['alignment']:
        for w in m['alignment']['words']:
            safe.add(w['start']);safe.add(w['end'])
            group=w.get('display_group')
            if group:
                a,b=display_intervals.get(group,(w['start'],w['end']))
                display_intervals[group]=(min(a,w['start']),max(b,w['end']))
    def crosses(n):
        return (m['alignment'] and any(w['start']<n<w['end'] for w in m['alignment']['words'])) or any(a<n<b for a,b in display_intervals.values())
    if intervals is None:
        if parts:
            if not 1<=parts<=1000:raise ValueError('Număr de părți invalid.')
            targets=[frames*i/parts for i in range(1,parts)]
        elif target:
            if target<=0:raise ValueError('Durată țintă invalidă.')
            targets=list(range(round(target*m['sample_rate']),frames,round(target*m['sample_rate'])))
        elif maximum_frames is not None:targets=[]
        else:raise ValueError('Alege --intervals, --parts, --target-seconds sau --max-seconds.')
        if not m['alignment']:raise ValueError('Alegerea automată a limitelor sigure necesită aliniere reală; folosește intervale manuale pentru tăieturi temporale.')
        # Prefer a pause after a sentence and keep the acoustic tail in the first part.
        # CTC emissions mark letters, not necessarily the end of the audible phoneme.
        sentence_pauses=[]
        words=(m.get('alignment') or {}).get('words',[])
        for word,following in zip(words,words[1:]):
            if word['spoken'].rstrip().endswith(('.', '!', '?')) and following['start']-word['end']>=round(.15*m['sample_rate']):
                middle=(word['end']+following['start'])//2
                if not crosses(middle):sentence_pauses.append(middle)
        # For automatic targets prefer a sentence pause within 10% of the total
        # duration (maximum 30 seconds); otherwise fall back to aligned boundaries.
        safe=sorted(n for n in safe if not crosses(n))
        def choose(t):
            nearby=[n for n in sentence_pauses if abs(n-t)<=min(frames*.1,30*m['sample_rate'])]
            return min(nearby or safe,key=lambda n:abs(n-t))
        if maximum_frames is not None and not parts and not target:
            # Greedy furthest safe boundary guarantees each emitted interval's
            # sample count. Never invent a cut inside an aligned word/group.
            bounds=[0];candidates=sorted(set(safe)|set(sentence_pauses))
            while frames-bounds[-1]>maximum_frames:
                cursor=bounds[-1];limit=cursor+maximum_frames
                available=[n for n in candidates if cursor<n<=limit]
                if not available:raise ValueError(f'Conflict durată maximă: nicio limită aliniată între eșantioanele {cursor+1} și {limit}.')
                # Prefer a sentence pause near the latest legal boundary.
                latest=max(available)
                pauses=[n for n in sentence_pauses if cursor<n<=limit and latest-n<=min(maximum_frames*.1,30*m['sample_rate'])]
                bounds.append(max(pauses) if pauses else latest)
            bounds.append(frames)
        else:bounds=[0]+sorted(set(choose(t) for t in targets)-{0,frames})+[frames]
        intervals=[[a,b] for a,b in zip(bounds,bounds[1:])]
    previous=0
    for a,b in intervals:
        if type(a) is not int or type(b) is not int or not 0<=a<b<=frames:raise ValueError('Interval în eșantioane invalid.')
        if mode=='partition' and a!=previous:raise ValueError('Partition trebuie să fie fără goluri/suprapuneri și în ordine.')
        if crosses(a) or crosses(b):raise ValueError('Limita taie un cuvânt aliniat sau un grup afișat.')
        if maximum_frames is not None and b-a>maximum_frames:raise ValueError(f'Conflict durată maximă: intervalul [{a}, {b}] depășește {maximum_frames} eșantioane. Schimbă limitele sau plafonul.')
        previous=b
    if mode=='partition' and previous!=frames:raise ValueError('Partition nu păstrează întregul material.')
    plan=dict(schema_version=1,kind='split',created_utc=now(),parent=reference(p,p),parent_id=m['id'],parent_sha256=reference(p,p)['sha256'],mode=mode,intervals=intervals,
              omitted_or_repeated=mode=='extract',requires_text_review=not bool(m['alignment']),status='planned')
    if maximum_frames is not None:plan.update(maximum_seconds=maximum,maximum_frames=maximum_frames)
    return p,m,plan


def apply_split(value,plan,prefix):
    p,m=load(value)
    if reference(p,p)['sha256']!=plan['parent_sha256']:raise ValueError('Material schimbat după planificare.')
    # Revalidate every interval and check all destinations before creating any child.
    split_plan(value,plan['mode'],plan['intervals'],maximum=plan.get('maximum_seconds'))
    paths=[new_path(f'{prefix}-{i:03d}') for i in range(1,len(plan['intervals'])+1)]
    result=[]
    for q,(a,b) in zip(paths,plan['intervals']):
        child=base(q.parent.name,m['sample_rate'],b-a)
        child['composition']=deepcopy(m['composition'])
        child['profiles']=deepcopy(m['profiles'])
        child['parents']=[reference(p,q,id=m['id'],start=a,end=b)]
        child['sources']=rebase_refs(m['sources'],p,q)
        for clip in m['timeline']:
            left=clip['timeline_start'];right=left+clip['end']-clip['start']
            start=max(a,left);end=min(b,right)
            if start<end:
                copied=deepcopy(clip);copied['source']=rebase_refs(clip['source'],p,q)
                copied.update(start=clip['start']+start-left,end=clip['start']+end-left,timeline_start=start-a)
                child['timeline'].append(copied)
        words=[]
        if m['alignment']:
            for w in m['alignment']['words']:
                if a<=w['start'] and w['end']<=b:
                    words.append(dict(w,start=w['start']-a,end=w['end']-a))
        if words:
            child['text_spoken']=' '.join(w['spoken'] for w in words)
            child['text_display']=' '.join(w.get('display',w['spoken']) for w in words if w.get('display',w['spoken']))
            child['text_original']=child['text_display']
            child['alignment']=local_alignment(rebase_refs(m['alignment'],p,q),words,child['timeline'])
            child['alignment_status']=m['alignment_status']
            child['text_units']=[dict(start=w['start'],end=w['end'],spoken=w['spoken'],display=w.get('display',w['spoken']),timing='word_import') for w in words]
        elif a==0 and b==m['frames']:
            for field in ('text_original','text_display','text_spoken','text_units'):child[field]=deepcopy(m[field])
        else:child['history'].append(dict(action='temporal_without_alignment',warning='Textul fragmentului nu este cunoscut; nu este inventat. Titlurile semantice necesită text furnizat.'))
        for s in m['scenes']:
            start=max(a,s['start']);end=min(b,s['end'])
            if start<end:
                scene=rebase_refs(deepcopy(s),p,q);scene.update(start=start-a,end=end-a)
                if scene['kind']=='video':
                    scene['source_start']=scene.get('source_start',0)+(start-s['start'])/m['sample_rate']
                if scene.get('asset_schema'):
                    for spec in [scene,*scene.get('profile_overrides',{}).values()]:
                        video=spec.get('video')
                        if video:
                            first=video.get('source_start',0)+(start-s['start'])/m['sample_rate'];last=video.get('source_end')
                            if last is not None and first>=last:
                                if scene.get('visual',{}).get('short_policy')=='loop':first=video.get('source_start',0)+(first-video.get('source_start',0))%(last-video.get('source_start',0))
                                else:first=max(video.get('source_start',0),last-1/30)
                            video['source_start']=first
                            if last is not None:video['source_end']=min(last,first+(end-start)/m['sample_rate'])
                            video['audio_enabled']=False
                scene['parent_scene_offset_samples']=start-s['start'];child['scenes'].append(scene)
        map_scene_text(child)
        child['history'].append(dict(action='split',mode=plan['mode'],interval=[a,b],parent=m['id'],created_utc=now(),motion_note='Mișcarea se reia local în scenele decupate.'))
        for scene in child['scenes']:
            if scene.get('asset_schema'):
                from .asset_scenes import context
                scene['context']=context(child,scene)
        write(q,child)
        if any(s.get('asset_schema') for s in child['scenes']):
            from .asset_scenes import credits
            credits(q)
        result.append(str(q))
    return result


def merge_plan(values,identifier):
    pairs=[load(v) for v in values]
    if not pairs:raise ValueError('Lista de materiale este goală.')
    if len(set(m['sample_rate'] for _,m in pairs))!=1:raise ValueError('Rate audio diferite: importă copii convertite explicit la aceeași rată înainte de merge. Nu se face resampling implicit.')
    q=new_path(identifier)
    return q,pairs,dict(kind='merge',created_utc=now(),order=[m['id'] for _,m in pairs],sources=[reference(p,q) for p,_ in pairs],status='planned')


def merge(values,identifier,plan_only=False):
    q,pairs,plan=merge_plan(values,identifier)
    if plan_only:return plan
    result=base(identifier,pairs[0][1]['sample_rate'],sum(m['frames'] for _,m in pairs))
    result['composition']=deepcopy(pairs[0][1]['composition'])
    result['profiles']=deepcopy(pairs[0][1]['profiles'])
    offset=0;words=[];all_aligned=all(m['alignment'] for _,m in pairs)
    for ordinal,(p,m) in enumerate(pairs):
        result['parents'].append(reference(p,q,id=m['id'],start=offset,end=offset+m['frames']))
        result['sources']+=rebase_refs(m['sources'],p,q)
        for clip in m['timeline']:
            c=rebase_refs(deepcopy(clip),p,q);c['timeline_start']+=offset;result['timeline'].append(c)
        for scene in m['scenes']:
            s=rebase_refs(deepcopy(scene),p,q);s['start']+=offset;s['end']+=offset;s['id']=f'{m["id"]}-{s["id"]}';
            if s.get('asset_schema'):s['scene_id']=s['id']
            result['scenes'].append(s)
        if all_aligned:
            for w in m['alignment']['words']:
                item=dict(w,start=w['start']+offset,end=w['end']+offset)
                if item.get('display_group'):item['display_group']=f'{ordinal}:{m["id"]}:{item["display_group"]}'
                words.append(item)
        offset+=m['frames']
    for field in ('text_original','text_display','text_spoken'):result[field]='\n\n'.join(m[field] for _,m in pairs)
    if words:
        result['alignment']=local_alignment(dict(schema_version=1,sample_rate=result['sample_rate'],provenance='rebased from parents',status='imported_not_reviewed'),words,result['timeline'])
        result['alignment']['parent_alignments']=[dict(material=m['id'],backend=m['alignment'].get('backend'),model=m['alignment'].get('model'),settings=m['alignment'].get('settings'),request=m['alignment'].get('request',m['alignment'].get('parent_alignment_request'))) for _,m in pairs]
        result['alignment']['normalization']=[dict(token=w['spoken'],target=w['alignment_target'],reason='Acoustic normalization inherited from aligned source') for w in words if 'alignment_target' in w and (any(c.isdigit() for c in w['spoken']) or re.search(r'[A-ZĂÂÎȘȚ]{2,}',w['spoken']))]
        result['alignment_status']='aligned_with_warnings' if result['alignment'].get('low_confidence') else 'imported_not_reviewed'
        result['text_units']=[dict(start=w['start'],end=w['end'],spoken=w['spoken'],display=w.get('display',w['spoken']),timing='word_import') for w in words]
    map_scene_text(result)
    result['history']=[dict(action='merge',plan=plan,created_utc=now(),normalization='off',voice_overlap=False)]
    write(q,result)
    if any(s.get('asset_schema') for s in result['scenes']):
        from .asset_scenes import credits
        credits(q)
    return str(q)
