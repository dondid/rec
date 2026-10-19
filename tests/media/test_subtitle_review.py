"""No production review decisions: synthetic fixtures and isolated output only."""
import json
from pathlib import Path
import pytest
from test_media import material
from rec_media import core,content,review,subtitles,subtitle_style,video


@pytest.fixture
def aligned(material,tmp_path):
    p,m,c,image,words=material
    content.import_alignment(p,words,'synthetic fixture, not human reviewed')
    p,m=core.load(p)
    for w in m['alignment']['words']:w['confidence']=.1
    core.write(p,m);core.write(p.parent/'alignment.json',m['alignment'])
    output=tmp_path/'review.json';r=review.report(p,output)
    decisions=tmp_path/'decisions.json'
    data=dict(r,reviewer='fixture reviewer only',reviewed_utc=core.now(),decisions=[dict(index=1,action='ADJUST_START',start=m['alignment']['words'][1]['start']+1)])
    core.write(decisions,data)
    return p,m,c,decisions,data


@pytest.mark.parametrize('field,value',[('alignment_key','bad'),('source_text_sha256','bad'),('audio_sha256','bad'),('reviewer',''),('reviewed_utc','2026-01-01'),('decisions',[])])
def test_review_identity_and_explicit_decisions(aligned,field,value):
    p,m,c,path,data=aligned;data[field]=value;core.write(path,data);before=core.sha(p)
    with pytest.raises(ValueError):review.apply(p,path)
    assert core.sha(p)==before and not (p.parent/'alignment-reviews').exists()


@pytest.mark.parametrize('decision',[dict(index=0,action='ADJUST_START',start=-1),dict(index=0,action='ADJUST_END',end=99999999),
    dict(index=0,action='ADJUST_BOTH',start=100,end=100),dict(index=1,action='ADJUST_START',start=0),
    dict(index=0,action='ACCEPT',start=1),dict(index=1,action='ADJUST_START',start=True)])
def test_invalid_timing_refused_before_writes(aligned,decision):
    p,m,c,path,data=aligned;data['decisions']=[decision];core.write(path,data)
    with pytest.raises(ValueError):review.apply(p,path)
    assert core.load(p)[1]==m


def test_review_only_explicit_units_and_exact_backups(aligned):
    p,m,c,path,data=aligned;raw=p.read_bytes();original=(p.parent/'alignment.json').read_bytes()
    result=review.apply(p,path,validate_only=True);assert result['untouched_units']==3 and p.read_bytes()==raw
    applied=review.apply(p,path);after=core.load(p)[1]
    for i in [0,2,3]:
        assert json.dumps(m['alignment']['words'][i],ensure_ascii=False)==json.dumps(after['alignment']['words'][i],ensure_ascii=False)
    assert after['alignment']['words'][1]['start']==m['alignment']['words'][1]['start']+1
    audit=Path(applied['journal']).parent
    assert (audit/'before-material.json').read_bytes()==raw
    assert (audit/'before-alignment.json').read_bytes()==original
    assert core.read(applied['report'])['explicit_indices']==[1]
    assert review.apply(p,path)['already_applied']


def test_review_interrupted_publication_resumes(aligned,monkeypatch):
    p,m,c,path,data=aligned;real=review.write
    def interrupted(target,value):
        if Path(target)==p:raise OSError('fixture publication failure')
        real(target,value)
    monkeypatch.setattr(review,'write',interrupted)
    with pytest.raises(OSError):review.apply(p,path)
    monkeypatch.setattr(review,'write',real)
    result=review.apply(p,path);assert result['already_applied']
    assert core.read(result['journal'])['phase']=='complete'


def test_source_and_audio_files_are_verified(aligned):
    p,m,c,path,data=aligned
    source=core.checked(p,m['timeline'][0]['source']);source.write_bytes(b'changed synthetic audio')
    with pytest.raises(ValueError):review.apply(p,path)


@pytest.mark.parametrize('size,profile',[([640,360],'landscape'),([360,640],'portrait')])
@pytest.mark.parametrize('mode',['classic','highlight','scroll'])
def test_caption_modes_unicode_timing_and_bounds(aligned,tmp_path,size,profile,mode):
    p,m,c,*_=aligned;c['font_min']=12
    result=subtitles.subtitle_files(p,m,tmp_path/(profile+mode),size,c,mode,profile)
    layout=core.read(result['layout']);ass=core.checked(p,result['ass']).read_text()
    assert 'Ștefan' in ass and 'Măriuca' in ass and m['alignment']==core.load(p)[1]['alignment']
    if mode=='highlight':
        events=layout['events'];assert set(e['active_index'] for e in events)>={0,1,2,3,None}
        assert all(m['alignment']['words'][e['active_index']]['start']<=e['start']<m['alignment']['words'][e['active_index']]['end'] for e in events if e['active_index'] is not None)
    if mode=='scroll':
        other=subtitles.subtitle_files(p,m,tmp_path/(profile+mode+'again'),size,c,mode,profile)
        assert core.checked(p,result['ass']).read_bytes()==core.checked(p,other['ass']).read_bytes()
    for e in layout['events']:
        x0,y0,x1,y1=e['region'];assert 0<=x0<x1<=size[0] and 0<=y0<y1<=size[1]
        assert r'\clip(' in e['text']


def test_ass_styles_profile_overrides_and_scene_identity(aligned,tmp_path):
    p,m,c,*_=aligned;original=video.scene_key(m['scenes'][0],[640,360],c,None,False)
    c['subtitle_style']=dict(preset='boxed',profiles={'portrait':dict(font_size=30,alignment=8,highlight_color='00FF00',line_spacing=12)})
    subtitle_style.validate(c);s=subtitle_style.effective(c,[360,640],'portrait')
    assert s['font_size']==30 and s['alignment']==8 and s['highlight_color']=='00FF00' and s['border_style']==3
    assert video.scene_key(m['scenes'][0],[640,360],c,None,False)==original


@pytest.mark.parametrize('spec',[{'preset':'bad'},{'outline':float('nan')},{'alignment':True},{'safe_area':[.4,.6,.5,.4]},
    {'color':'red'},{'profiles':{'portrait':{'unknown':1}}},{'scroll_lines':1},{'font':'/missing.ttf'}])
def test_invalid_ass_config(spec,material):
    c=material[2];c['subtitle_style']=spec
    with pytest.raises(ValueError):subtitle_style.validate(c)


def test_ass_escape_no_user_override(aligned,tmp_path):
    p,m,c,*_=aligned
    m['alignment']['words'][0]['display']=r'Ș{\pos(0,0)}'
    result=subtitles.subtitle_files(p,m,tmp_path/'escaped',[640,360],c,'highlight')
    ass=core.checked(p,result['ass']).read_text();assert r'Ș\{\\pos(0,0)\}' in ass


def test_highlight_pixels_change_and_pause_is_neutral(aligned,tmp_path):
    import subprocess
    from PIL import Image
    p,m,c,*_=aligned
    result=subtitles.subtitle_files(p,m,tmp_path/'hot',[640,360],c,'highlight')
    args=[core.tool('ffmpeg'),'-nostdin','-v','error','-threads','2','-f','lavfi','-i','color=c=black:s=640x360:r=30:d=2.4',
        '-filter_threads','1','-vf',"ass=filename=hot/subtitles.ass:fontsdir=hot/fonts,select='eq(n,7)+eq(n,16)+eq(n,25)'",
        '-fps_mode','vfr','-threads','2','-pix_fmt','rgb24','-f','rawvideo','pipe:1']
    r=subprocess.run(args,cwd=tmp_path,capture_output=True);assert r.returncode==0,r.stderr
    length=640*360*3;assert len(r.stdout)==length*3
    masks=[]
    for i in range(3):
        im=Image.frombytes('RGB',(640,360),r.stdout[i*length:(i+1)*length])
        masks.append({j for j,(red,green,blue) in enumerate(im.getdata()) if red>160 and green>160 and blue<100})
    assert len(masks[0])>5 and not masks[1] and len(masks[2])>5
    assert len(masks[0]^masks[2])>10
    rect=core.read(result['layout'])['events'][0]['region']
    assert all(rect[0]<=n%640<rect[2] and rect[1]<=n//640<rect[3] for mask in masks for n in mask)


def test_fallback_floor_and_title_reserved_region(aligned,tmp_path):
    p,m,c,*_=aligned
    m['scenes'][0]['review_status']='FALLBACK'
    result=subtitles.subtitle_files(p,m,tmp_path/'fallback',[1920,1080],c,'classic')
    assert all(e['region'][3]<=1080*.86 for e in core.read(result['layout'])['events'])
    c['subtitle_style']=dict(alignment=8,safe_area=[.06,.02,.06,.10])
    title='Verificare titlu'
    _,box=content.text_layer((640,360),title,c,'top')
    other=subtitles.subtitle_files(p,m,tmp_path/'title',[640,360],c,'classic',title=title)
    assert all(e['position'][1]>=box['text_box'][3]+18 for e in core.read(other['layout'])['events'])
