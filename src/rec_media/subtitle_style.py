"""Final-composition typography. None of these options alter scene pixels."""
import math
import re
from pathlib import Path
from copy import deepcopy

PRESETS={'safe':{},'boxed':dict(border_style=3,outline=2,shadow=0,background='B0000000'),
         'minimal':dict(outline=1,shadow=0)}
FIELDS={'font','font_size','outline','shadow','margin_x','margin_v','alignment','line_spacing',
        'color','highlight_color','highlight_bold','outline_color','background','safe_area','scroll_seconds','scroll_lines','border_style'}


def validate(c,base=None):
    spec=c.get('subtitle_style',{})
    if not isinstance(spec,dict) or set(spec)-FIELDS-{'preset','profiles'}:raise ValueError('subtitle_style invalid.')
    if not isinstance(spec.get('preset','safe'),str) or spec.get('preset','safe') not in PRESETS:raise ValueError('Preset ASS necunoscut.')
    profiles=spec.get('profiles',{})
    if not isinstance(profiles,dict) or set(profiles)-{'landscape','portrait','square','custom'}:raise ValueError('Profile ASS invalide.')
    for values in [spec,*profiles.values()]:
        if not isinstance(values,dict) or (values is not spec and set(values)-FIELDS):raise ValueError('Override ASS invalid.')
        for field,v in values.items():
            if field in ('preset','profiles'):continue
            if field in ('color','highlight_color','outline_color'):
                if not isinstance(v,str) or not re.fullmatch('[0-9A-Fa-f]{6}',v):raise ValueError(f'ASS {field} invalid.')
            elif field=='background':
                if not isinstance(v,str) or not re.fullmatch('[0-9A-Fa-f]{8}',v):raise ValueError('ASS background cere AARRGGBB.')
            elif field=='font':
                if not isinstance(v,str) or not v.strip():raise ValueError('Font ASS invalid.')
                f=Path(v);f=(Path(base or '.')/f).resolve() if not f.is_absolute() else f
                if not f.is_file():raise ValueError('Font ASS local lipsă.')
                values[field]=str(f)
            elif field=='safe_area':
                if not isinstance(v,list) or len(v)!=4 or any(type(x) not in (int,float) or not math.isfinite(x) or not 0<=x<.8 for x in v) or v[0]+v[2]>=.8 or v[1]+v[3]>=.9:raise ValueError('ASS safe_area invalid [left,top,right,bottom].')
            elif field=='highlight_bold':
                if type(v) is not bool:raise ValueError('highlight_bold cere boolean.')
            else:
                limits={'font_size':(12,200),'outline':(0,8),'shadow':(0,8),'margin_x':(.02,.4),'margin_v':(.02,.4),
                        'alignment':(1,9),'line_spacing':(0,60),'scroll_seconds':(.04,2),'scroll_lines':(2,5),'border_style':(1,3)}
                low,high=limits[field]
                if type(v) not in (int,float) or not math.isfinite(v) or not low<=v<=high:raise ValueError(f'ASS {field} invalid.')
                if field in ('font_size','alignment','scroll_lines','border_style') and type(v) is not int:raise ValueError(f'ASS {field} cere întreg.')
                if field=='border_style' and v not in (1,3):raise ValueError('ASS border_style este 1 sau 3.')
    return c


def effective(c,size,profile=None):
    name=profile if profile in ('landscape','portrait','square','custom') else ('portrait' if size[1]>size[0] else 'landscape' if size[0]>size[1] else 'square')
    spec=deepcopy(c.get('subtitle_style',{}));preset=spec.pop('preset','safe');profiles=spec.pop('profiles',{})
    result=dict(font=c['font'],font_size=min(c['subtitle_font_size'],round(size[0]/22)),outline=c.get('subtitle_outline',3),
        shadow=1,margin_x=.06,margin_v=.10 if name=='portrait' else .12,alignment=2,line_spacing=4,
        color=c['subtitle_color'],highlight_color='FFFF00',highlight_bold=False,outline_color='101010',background='80000000',
        safe_area=[.06,.52,.06,.10],scroll_seconds=.18,scroll_lines=3,border_style=1)
    result.update(PRESETS[preset]);result.update(spec);result.update(profiles.get(name,{}));result['profile']=name;result['preset']=preset
    if result['font_size']<c['font_min']:raise ValueError('Profil prea mic pentru fontul minim de subtitrare.')
    return result
