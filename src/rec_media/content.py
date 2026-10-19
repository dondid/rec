"""Inspectable alignment, subtitles, extractive titles and local typography."""
import math
from pathlib import Path
import re
from collections import Counter

from .core import checked, key, load, now, read, reference, resolve, sha, write


def import_alignment(value, path, provenance):
    p,m=load(value);data=read(path)
    if data.get('sample_rate')!=m['sample_rate'] or data.get('audio_timeline_hash')!=key(m['timeline']):
        raise ValueError('Aliniere pentru alt audio/rata/cronologie. Folosește timeline_hash din material.')
    words=data['words'];previous=0
    if not words or ' '.join(w['spoken'] for w in words).split()!=m['text_spoken'].split():
        raise ValueError('Cuvintele alinierii nu acoperă exact textul rostit cunoscut.')
    for w in words:
        if (type(w['start']) is not int or type(w['end']) is not int or
            not previous<=w['start']<w['end']<=m['frames']):raise ValueError('Intervale aliniere invalide.')
        if not isinstance(w.get('display',w['spoken']),str):raise ValueError('Text afișat invalid.')
        previous=w['end']
    group_labels={};closed=set();last_group=None
    for w in words:
        group=w.get('display_group')
        if group:
            if not isinstance(group,str) or group in closed:raise ValueError('Grup afișat necontiguu/invalid.')
            label=w.get('display',w['spoken'])
            if group in group_labels and group_labels[group]!=label:raise ValueError('Grupul afișat necesită aceeași etichetă pe fiecare cuvânt rostit.')
            group_labels[group]=label
        if last_group and last_group!=group:closed.add(last_group)
        last_group=group
    m['alignment']=dict(schema_version=1,sample_rate=m['sample_rate'],audio_timeline_hash=key(m['timeline']),words=words,
                        provenance=provenance,source=reference(path,p),created_utc=now(),status='imported_not_reviewed')
    m['alignment_status']='imported_not_reviewed'
    m['text_units']=[dict(start=w['start'],end=w['end'],spoken=w['spoken'],display=w.get('display',w['spoken']),timing='word_import') for w in words]
    write(p.parent/'alignment.json',m['alignment']);write(p,m)
    return m['alignment']


def valid_words(m):
    a=m.get('alignment')
    if not a or a['audio_timeline_hash']!=key(m['timeline']):raise ValueError('Lipsește alinierea reală pentru cronologia curentă. Importă timpi; nu se estimează din lungimea textului.')
    if ' '.join(w['spoken'] for w in a['words']).split()!=m['text_spoken'].split():
        raise ValueError('Textul rostit s-a schimbat; refă alinierea.')
    if any(w.get('review',{}).get('status')=='rejected' for w in a['words']):raise ValueError('Aliniere cu unități rejected; corectează sau rerulează segmentele afectate.')
    return a['words']


def groups(m, max_words=7):
    words=valid_words(m);result=[];part=[]
    for w in words:
        same_group=part and w.get('display_group') and w.get('display_group')==part[-1].get('display_group')
        if part and not same_group and (len(part)>=max_words or w['start']-part[-1]['end']>m['sample_rate']*0.6):
            result.append(part);part=[]
        part.append(w)
    if part:result.append(part)
    return result


def displayed(words):
    labels=[];seen=set()
    for w in words:
        group=w.get('display_group')
        if group and group in seen:continue
        if group:seen.add(group)
        label=w.get('display',w['spoken'])
        if label:labels.append(label)
    return ' '.join(labels)


def ass_escape(text):
    return text.replace('\\','\\\\').replace('{','\\{').replace('}','\\}').replace('\n',r'\N')


def stamp(frame,rate,ass=False):
    # Round once, at export; internal timing is always integer samples.
    units=(frame*(100 if ass else 1000)+rate//2)//rate
    fraction=units%(100 if ass else 1000);seconds=units//(100 if ass else 1000)
    h=seconds//3600;minute=(seconds//60)%60;sec=seconds%60
    return f'{h}:{minute:02}:{sec:02}.{fraction:02}' if ass else f'{h:02}:{minute:02}:{sec:02},{fraction:03}'


def subtitle_files(document,m,directory,size,c,mode='classic'):
    from PIL import ImageFont
    if mode not in ('classic','highlight','scroll'):raise ValueError('Mod subtitrare invalid.')
    pieces=groups(m);directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    width,height=size; margin=round(min(size)*c['safe_margin'])
    # Layout measured independently for each profile.
    font_size=min(c['subtitle_font_size'],round(width/22))
    if font_size<c['font_min']:raise ValueError('Profil prea mic pentru fontul minim de subtitrare.')
    font=ImageFont.truetype(c['font'],font_size)
    family=font.getname()[0].replace(',',' ')
    import shutil
    (directory/'fonts').mkdir(exist_ok=True)
    shutil.copyfile(c['font'],directory/'fonts/font.ttf')
    def lines(text):
        output=['']
        for word in text.split():
            candidate=(output[-1]+' '+word).strip()
            if font.getlength(candidate)>width-2*margin:
                if font.getlength(word)>width-2*margin:raise ValueError('Cuvânt prea lat pentru subtitrare.')
                output.append(word)
            else:output[-1]=candidate
        if len(output)>2:raise ValueError('Subtitrare peste două linii; regrupează cuvintele/configurează fontul.')
        return '\n'.join(output)
    # Split large groups to fit up to two lines, without losing aligned words.
    fitted=[]
    for g in pieces:
        current=[]
        for w in g:
            try:lines(displayed(current+[w]))
            except ValueError:
                if not current:raise
                fitted.append(current);current=[]
            current.append(w)
        if current:fitted.append(current)
    srt=[];events=[]
    rgb=c['subtitle_color'];bgr=rgb[4:6]+rgb[2:4]+rgb[:2]
    header=f'''[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{family},{font_size},&H00{bgr},&H0000FFFF,&H00101010,&H80000000,0,0,0,0,100,100,0,0,1,{c.get('subtitle_outline',3)},1,2,{margin},{margin},{max(margin,round(height*c.get('subtitle_margin_v',.07)))},1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    for index,g in enumerate(fitted,1):
        text=lines(displayed(g));start=g[0]['start'];end=g[-1]['end']
        srt.append(f'{index}\n{stamp(start,m["sample_rate"])} --> {stamp(end,m["sample_rate"])}\n{text}\n')
        if mode=='classic':
            events.append((start,end,ass_escape(text)))
        else:
            for j,w in enumerate(g):
                # Real imported word intervals; pauses retain the prior window only until next word.
                stop=g[j+1]['start'] if j+1<len(g) else w['end']
                if mode=='highlight':
                    # Keep the whole phrase and overlay a highlighted word; explicit display mappings remain visible.
                    tokens=[];seen_groups=set()
                    for k,v in enumerate(g):
                        group=v.get('display_group')
                        if group and group in seen_groups:continue
                        if group:seen_groups.add(group)
                        token=v.get('display',v['spoken'])
                        if not token:continue
                        active=k==j or (group and group==w.get('display_group'))
                        tokens.append((r'{\c&H00FFFF&}' if active else '')+ass_escape(token)+(r'{\r}' if active else ''))
                    # Preserve measured wrapping by applying hard line breaks at display-space indices.
                    rendered=' '.join(tokens)
                    if '\n' in text:
                        cutoff=len(text.split('\n')[0].split());seen=0;chunks=[]
                        for token in tokens:
                            if seen==cutoff:chunks.append(r'\N')
                            chunks.append(token);seen+=1
                        rendered=' '.join(chunks).replace(' '+r'\N'+' ',r'\N')
                else:
                    rendered=ass_escape(lines(displayed(g[max(0,j-2):j+4])))
                events.append((w['start'],stop,rendered))
    ass=header+''.join(f'Dialogue: 0,{stamp(a,m["sample_rate"],True)},{stamp(b,m["sample_rate"],True)},Default,,0,0,0,,{text}\n' for a,b,text in events)
    for name,text in [('subtitles.srt','\n'.join(srt)),('subtitles.ass',ass)]:
        (directory/name).write_text(text,encoding='utf-8')
    from .derive import rebase_refs
    write(directory/'alignment.json',rebase_refs(m['alignment'],document,directory/'alignment.json'))
    return dict(mode=mode,srt=reference(directory/'subtitles.srt',document),ass=reference(directory/'subtitles.ass',document),alignment=reference(directory/'alignment.json',document))


def titles(value,c,manual=None,select=None,approve=False,unlock=False):
    p,m=load(value);state=m['titles']
    if state['locked'] and not unlock and (manual or select or approve):raise ValueError('Titlu aprobat/blocat; folosește --unlock explicit.')
    text=m['text_spoken'] or m['text_display']
    sentences=[x.strip() for x in re.split(r'(?<=[.!?])\s+|\n+',text) if x.strip()]
    passages=[]
    for sentence in sentences:
        if len(sentence)<=c['title_max_chars']:passages.append(sentence);continue
        # Contiguous extracts from long sentences, with visible source evidence.
        clauses=[x.strip() for x in re.split(r'[;:—]|,\s+',sentence) if x.strip()]
        for clause in clauses:
            words=clause.split();excerpt=[]
            for word in words:
                if len(' '.join(excerpt+[word]))>min(c['title_max_chars'],c['thumbnail_max_chars']):break
                excerpt.append(word)
            if len(excerpt)>=3:passages.append(' '.join(excerpt))
    sentences=passages
    freq=Counter(w.casefold() for w in re.findall(r'\w{4,}',text))
    ranked=[]
    for index,s in enumerate(sentences):
        if len(s)>c['title_max_chars'] or len(s)<10:continue
        score=sum(freq[w.casefold()] for w in re.findall(r'\w{4,}',s))/max(1,len(s.split()))
        ranked.append((-score,index,s))
    candidates=[];seen=set()
    for _,index,s in sorted(ranked):
        identity=re.sub(r'\W+','',s.casefold())
        if identity in seen:continue
        seen.add(identity)
        candidates.append(dict(candidate_id=key(s)[:12],title=s,thumbnail_text=s if len(s)<=c['thumbnail_max_chars'] else None,
                               source_sentence=index,source_passage=s,source_char_range=[text.find(s),text.find(s)+len(s)],backend='extractive',version=1,state='suggested'))
        if len(candidates)==c['title_candidates']:break
    if manual:
        if not manual.strip() or len(manual)>c['title_max_chars']:raise ValueError('Titlu manual gol/prea lung.')
        candidates.insert(0,dict(candidate_id=key(manual)[:12],title=manual,thumbnail_text=manual if len(manual)<=c['thumbnail_max_chars'] else None,
                                 source_passage=None,backend='manual',version=1,state='suggested'))
        select=candidates[0]['candidate_id']
    if select:
        selected=next((x for x in candidates if x['candidate_id']==select),None)
        if not selected:raise ValueError('candidate_id inexistent.')
        selected['state']='approved' if approve else 'selected'
    else:selected=None
    if state['locked'] and not unlock:
        selected=state['selected']
    m['titles']=dict(candidates=candidates,selected=selected,locked=state['locked'] if not unlock and state['locked'] else bool(approve and selected),needs_edit=not bool(candidates))
    m['thumbnail_text']=selected.get('thumbnail_text') if selected else None
    write(p.parent/'titles.json',m['titles']);write(p,m)
    return m['titles']


def fit_image(image,size,fit='contain',focal=(.5,.5)):
    from PIL import Image, ImageOps
    image=ImageOps.exif_transpose(image).convert('RGB')
    if fit=='contain':return ImageOps.pad(image,size,color='#14232f',centering=(.5,.5))
    if fit!='cover':raise ValueError('Încadrare invalidă.')
    return ImageOps.fit(image,size,centering=tuple(focal))


def text_layer(size,text,c,variant='panel'):
    from PIL import Image, ImageDraw, ImageFont
    width,height=size;image=Image.new('RGBA',size,(0,0,0,0));draw=ImageDraw.Draw(image)
    margin=round(min(size)*c['safe_margin']);limit=width-2*margin
    if not text or len(text)>c['thumbnail_max_chars']:raise ValueError('Textul thumbnail-ului este gol/prea lung; editează-l explicit.')
    chosen=None
    for fs in range(c['thumbnail_font_size'],c['font_min']-1,-2):
        font=ImageFont.truetype(c['font'],fs);lines=['']
        for word in text.split():
            candidate=(lines[-1]+' '+word).strip()
            if draw.textlength(candidate,font=font)>limit:lines.append(word)
            else:lines[-1]=candidate
        if not lines[0]:lines=lines[1:]
        txt='\n'.join(lines);box=draw.multiline_textbbox((0,0),txt,font=font,spacing=fs//5,stroke_width=2)
        if box[2]-box[0]<=limit and box[3]-box[1]<=height*.42:
            chosen=(font,txt,box,fs);break
    if not chosen:raise ValueError('Textul nu încape la fontul minim; editează-l.')
    font,txt,box,fs=chosen;h=box[3]-box[1]
    y=margin if variant=='top' else height-margin-h-12
    draw.rounded_rectangle((margin-10,y-10,width-margin+10,y+h+16),radius=12,fill=(10,20,30,215))
    draw.multiline_text((margin,y-box[1]),txt,font=font,fill='white',spacing=fs//5,stroke_width=2,stroke_fill='black')
    return image,dict(font_size=fs,text_box=[margin,y,width-margin,y+h],variant=variant,font_sha256=sha(c['font']))


def thumbnail(value,directory,profiles,c,text=None,image=None,scene=None,variant='panel',fmt='png'):
    from PIL import Image, ImageDraw
    p,m=load(value)
    selected=m['titles'].get('selected')
    text=text or m.get('thumbnail_text') or (selected or {}).get('thumbnail_text')
    if not text:raise ValueError('Alege un titlu/text scurt explicit pentru thumbnail.')
    folder=Path(directory);folder.mkdir(parents=True,exist_ok=True);outputs=[]
    visual=None;anchor=None
    if image:visual=Path(image).resolve()
    elif scene:
        anchor=next((s for s in m['scenes'] if s['id']==scene),None)
        if not anchor:raise ValueError('Scenă inexistentă.')
        visual=checked(p,anchor['asset'])
    for name,size in profiles.items():
        dest=folder/f'{name}-{variant}.{fmt}'
        if dest.exists():raise ValueError(f'Thumbnail existent: {dest}')
        if visual:
            if anchor and anchor.get('kind')=='video':
                from .core import ff
                frame=folder/f'.{name}-scene.png'
                ff(['-ss',str((anchor['end']-anchor['start'])/m['sample_rate']/2),'-i',visual,'-frames:v','1',frame]);background=Image.open(frame)
            else:background=Image.open(visual)
            background=fit_image(background,tuple(size),c['fit'],(anchor or {}).get('focal',[.5,.5]))
        else:
            background=Image.new('RGB',size,'#14232f');d=ImageDraw.Draw(background)
            d.polygon([(0,0),(size[0],0),(0,size[1])],fill='#24556a')
            d.ellipse((size[0]*.5,size[1]*.1,size[0]*1.1,size[1]*.7),fill='#247f88')
        layer,layout=text_layer(tuple(size),text,c,variant)
        result=Image.alpha_composite(background.convert('RGBA'),layer).convert('RGB')
        result.save(dest,format='PNG' if fmt=='png' else 'JPEG')
        meta=dict(material=m['id'],created_utc=now(),text=text,profile=name,size=size,layout=layout,
                  visual=reference(visual,dest) if visual else None,scene=scene,interval=[anchor['start'],anchor['end']] if anchor else None,
                  mode='scene' if anchor else ('image' if visual else 'graphic_cover'),sha256=sha(dest),visual_review_status='not_reviewed')
        write(dest.with_suffix('.json'),meta);outputs.append(str(dest))
    return outputs
