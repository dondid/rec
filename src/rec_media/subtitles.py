"""Measured classic/highlight and continuous line scrolling, using observed timing."""
import math
import shutil
from pathlib import Path
from PIL import ImageFont
from . import core,content,subtitle_style


def bgr(rgb):return rgb[4:6]+rgb[2:4]+rgb[:2]


def subtitle_files(document,m,directory,size,c,mode='classic',profile=None,title=None):
    if mode not in ('classic','highlight','scroll'):raise ValueError('Mod subtitrare invalid.')
    words=content.valid_words(m);style=subtitle_style.effective(c,size,profile)
    font=ImageFont.truetype(style['font'],style['font_size']);w,h=size;rate=m['sample_rate']
    from .asset_scenes import effective
    scenes=[effective(s,style['profile']) if s.get('asset_schema') else s for s in m.get('scenes',[])]
    def scene_at(sample):return next((s for s in scenes if s['start']<=sample<s['end']),{})
    def region(scene):
        left,top,right,bottom=style['safe_area'];mx=style['margin_x'];mv=style['margin_v']
        if scene.get('selected_asset',{}).get('provider')=='graphic' or scene.get('review_status')=='FALLBACK':mv=max(mv,.10 if h>w else .14)
        x0=math.ceil(w*max(left,mx));x1=math.floor(w*(1-max(right,mx)))
        y0=math.ceil(h*top);y1=math.floor(h*(1-max(bottom,mv)))
        # Pixel-identical title generator is only measured here, never changed.
        for text in [title,scene.get('title_overlay'),scene.get('overlay')]:
            if text:
                top_overlay=text in (title,scene.get('title_overlay'))
                _,box=content.text_layer(tuple(size),text,c,'top' if top_overlay else 'panel')
                if top_overlay:y0=max(y0,math.ceil(box['text_box'][3]+18))
                else:y1=min(y1,math.floor(box['text_box'][1]-18))
        if y1<=y0:raise ValueError('Title/overlay nu lasă safe area pentru subtitrare.')
        return [x0,y0,x1,y1]
    padding=math.ceil(style['outline']+style['shadow']+3)
    lh=math.ceil(style['font_size']*1.35+style['line_spacing'])
    units=[]
    for i,word in enumerate(words):
        label=word.get('display',word['spoken']);group=word.get('display_group')
        if group and units and units[-1].get('group')==group:
            units[-1]['indices'].append(i);units[-1]['end']=word['end'];continue
        if not label:continue
        units.append(dict(label=label,start=word['start'],end=word['end'],indices=[i],group=group))
    def wrap(items,rect):
        lines=[[]];limit=rect[2]-rect[0]-2*padding
        for unit in items:
            if font.getlength(unit['label'])>limit:raise ValueError('Cuvânt/unitate prea lată pentru safe area.')
            text=' '.join(u['label'] for u in [*lines[-1],unit])
            if lines[-1] and font.getlength(text)>limit:lines.append([])
            lines[-1].append(unit)
        return lines
    chunks=[];current=[]
    for unit in units:
        rect=region(scene_at(unit['start']))
        split=current and (scene_at(current[0]['start']).get('id')!=scene_at(unit['start']).get('id') or
              unit['start']-current[-1]['end']>.6*rate or len(current)>=12 or len(wrap([*current,unit],rect))>2)
        if split:chunks.append(current);current=[]
        current.append(unit)
    if current:chunks.append(current)
    events=[];quantized=[];srt=[];layout=[]
    def emit(start,end,text,rect,x,y,active=None,motion=None):
        if content.stamp(start,rate,True)==content.stamp(end,rate,True):quantized.append([start,end]);return
        col=(style['alignment']-1)%3;anchor=7+col
        pos=rf'\pos({x},{y})' if motion is None else rf'\move({x},{y+lh},{x},{y},0,{motion})'
        tags=rf'{{\an{anchor}{pos}\clip({",".join(map(str,rect))})}}'
        events.append(dict(start=start,end=end,text=tags+text,active_index=active,region=rect,position=[x,y],motion_ms=motion))
    def place(rect,count,scene):
        if count*lh+2*padding>rect[3]-rect[1]:raise ValueError('Liniile ASS nu încap în safe area; ajustează font/spacing/scroll_lines.')
        col=(style['alignment']-1)%3;row=(style['alignment']-1)//3
        if scene.get('subtitle_placement')=='top':row=2
        x=[rect[0]+padding,(rect[0]+rect[2])//2,rect[2]-padding][col]
        y=rect[3]-count*lh-padding if row==0 else (rect[1]+rect[3]-count*lh)//2 if row==1 else rect[1]+padding
        return x,y
    for i,chunk in enumerate(chunks,1):
        scene=scene_at(chunk[0]['start']);rect=region(scene);lines=wrap(chunk,rect);start=chunk[0]['start'];end=chunk[-1]['end']
        text='\n'.join(' '.join(u['label'] for u in line) for line in lines)
        srt.append(f'{i}\n{content.stamp(start,rate)} --> {content.stamp(end,rate)}\n{text}\n')
        layout.append(dict(start=start,end=end,region=rect,lines=text.splitlines(),line_height=lh))
        if mode=='scroll':continue
        x,y=place(rect,len(lines),scene)
        bounds=sorted({start,end,*[v for u in chunk for j in u['indices'] for v in (words[j]['start'],words[j]['end'])]}) if mode=='highlight' else [start,end]
        for a,b in zip(bounds,bounds[1:]):
            active=next((j for u in chunk for j in u['indices'] if words[j]['start']<=a<words[j]['end']),None) if mode=='highlight' else None
            for n,line in enumerate(lines):
                tokens=[]
                for u in line:
                    token=content.ass_escape(u['label'])
                    if active in u['indices']:
                        token=rf'{{\c&H{bgr(style["highlight_color"])}&\b{int(style["highlight_bold"])}}}'+token+rf'{{\c&H{bgr(style["color"])}&\b0}}'
                    tokens.append(token)
                emit(a,b,' '.join(tokens),rect,x,y+n*lh,active)
    if mode=='scroll':
        # Wrap once per scene, then move by exactly one measured line at boundaries.
        line_rows=[]
        for scene in (scenes or [dict(start=0,end=m['frames'])]):
            selected=[u for u in units if scene['start']<=u['start']<scene['end']]
            if not selected:continue
            rect=region(scene);lines=wrap(selected,rect);count=style['scroll_lines'];x,y=place(rect,count,scene)
            for i,line in enumerate(lines):
                start=line[0]['start'];end=lines[i+1][0]['start'] if i+1<len(lines) else line[-1]['end']
                movement=min(round(style['scroll_seconds']*1000),max(1,round((end-start)/rate*500))) if i else None
                for offset in range(count+1):
                    j=i+offset-1
                    if not 0<=j<len(lines):continue
                    emit(start,end,' '.join(content.ass_escape(u['label']) for u in lines[j]),rect,x,y+offset*lh,motion=movement)
                line_rows.append(dict(start=start,end=end,line=i,region=rect,position=[x,y],motion_ms=movement))
        layout=line_rows
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True);(directory/'fonts').mkdir(exist_ok=True)
    shutil.copyfile(style['font'],directory/'fonts/font.ttf')
    family=font.getname()[0].replace(',',' ');bg=style['background'];back=bg[:2]+bgr(bg[2:])
    header=f'''[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{family},{style['font_size']},&H00{bgr(style['color'])},&H00{bgr(style['highlight_color'])},&H00{bgr(style['outline_color'])},&H{back},0,0,0,0,100,100,0,0,{style['border_style']},{style['outline']},{style['shadow']},{style['alignment']},0,0,0,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    ass=header+''.join(f'Dialogue: 0,{content.stamp(e["start"],rate,True)},{content.stamp(e["end"],rate,True)},Default,,0,0,0,,{e["text"]}\n' for e in events)
    (directory/'subtitles.ass').write_text(ass,encoding='utf-8');(directory/'subtitles.srt').write_text('\n'.join(srt),encoding='utf-8')
    from .derive import rebase_refs
    core.write(directory/'alignment.json',rebase_refs(m['alignment'],document,directory/'alignment.json'))
    core.write(directory/'layout.json',dict(mode=mode,style=style,size=size,events=events,layout=layout,quantized_zero_intervals=quantized,
               timing_status='existing_alignment_not_human_verified',listening_review='not_listened'))
    return dict(mode=mode,ass=core.reference(directory/'subtitles.ass',document),srt=core.reference(directory/'subtitles.srt',document),alignment=core.reference(directory/'alignment.json',document),layout=str(directory/'layout.json'))
