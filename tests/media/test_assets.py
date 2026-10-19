"""Synthetic fixtures and injected HTTP only; never depend on live providers."""
import io
import json
import math
from pathlib import Path
import socket
import subprocess
import pytest
from PIL import Image
from test_media import material
from rec_media import core, video, derive, content
from rec_media import asset_http as http, asset_providers as providers, asset_library as library, asset_scenes as scenes


def image(tmp_path, color='red'):
    p=tmp_path/(color+'.png');Image.new('RGB',(320,240),color).save(p);return p


def metadata(identifier='one', **kwargs):
    value=providers.candidate('commons',identifier,'Romania parliament','https://images.example/'+identifier,
                             'https://commons.wikimedia.org/wiki/File:'+identifier,'Photographer','CC BY 4.0',
                             'https://creativecommons.org/licenses/by/4.0/',width=1000,height=800)
    value.update(kwargs);return value


class Response(io.BytesIO):
    def __init__(self,payload,mime='image/png',size=None):
        super().__init__(payload);self.headers={'Content-Type':mime,'Content-Length':str(len(payload) if size is None else size)}


def test_provider_parsing_and_unknown_license():
    payload={'query':{'pages':{'1':{'pageid':1,'title':'File:Romania','imageinfo':[dict(url='https://images.example/photo.png',mime='image/png',width=800,height=600,
                descriptionurl='https://commons.wikimedia.org/wiki/File:Romania',extmetadata={'Artist':{'value':'<b>Creator</b>'},'LicenseShortName':{'value':'CC BY 4.0'},'LicenseUrl':{'value':'https://creativecommons.org/licenses/by/4.0/'}})]}}}}
    urls=[]
    def get(url):urls.append(url);return payload
    a=providers.Commons().search('România',get=get)[0]
    assert a['creator']=='Creator' and a['provenance_complete'] and 'gsrnamespace=6' in urls[0]
    assert a['candidate_id']==providers.Commons().search('Romania',get=get)[0]['candidate_id']
    payload['query']['pages']['1']['imageinfo'][0]['extmetadata']={}
    a=providers.Commons().search('x',get=get)[0];assert a['license']==providers.UNKNOWN and not a['provenance_complete']
    ov={'results':[dict(id='o1',url='https://images.example/a.jpg',foreign_landing_url='https://example.org/source',creator='Author',license='by',license_version='4.0',license_url='https://creativecommons.org/licenses/by/4.0/',width=600,height=400,tags=[{'name':'Romania'}]) ]}
    assert providers.Openverse().search('q',get=lambda u:ov)[0]['tags']==['Romania']
    assert providers.Openverse().search('q','video',get=lambda u:pytest.fail('no video endpoint'))==[]


def test_pexels_optional_key_and_attribution(monkeypatch):
    monkeypatch.delenv('PEXELS_API_KEY',raising=False)
    with pytest.raises(ValueError,match='PEXELS_API_KEY'):providers.Pexels().search('q')
    monkeypatch.setenv('PEXELS_API_KEY','synthetic-secret')
    def get(url,headers):
        assert headers['Authorization']=='synthetic-secret' and '/v1/videos/search?' in url
        return dict(videos=[dict(id=1,url='https://pexels.com/video/1',width=320,height=240,duration=5,user={'name':'Author'},video_files=[dict(file_type='video/mp4',width=320,height=240,link='https://videos.pexels.com/1.mp4')])])
    a=providers.Pexels().search('q','video',get=get)[0]
    assert 'Pexels' in a['attribution'] and 'synthetic-secret' not in json.dumps(a)


@pytest.mark.parametrize('url',['file:///etc/passwd','ftp://example.org/a','http://127.0.0.1/a','http://169.254.169.254/','https://user:password@example.org/a','https://localhost/a','https://example.org:444/a','https://example.org/a\nb','https://[::1]/a'])
def test_invalid_url(url):
    with pytest.raises(ValueError):http.validate_url(url,resolve=False)


def test_dns_and_redirect_validation(monkeypatch):
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**k:[(None,None,None,None,('10.0.0.1',443))])
    with pytest.raises(ValueError,match='privată'):http.validate_url('https://public.example/a')
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**k:[(None,None,None,None,('8.8.8.8',443))])
    assert http.validate_url('https://public.example/a')
    from urllib.request import Request
    req=Request('https://public.example/a',headers={'Authorization':'secret'})
    redir=http.Redirects().redirect_request(req,None,302,'',{},'https://other.example/a')
    assert redir.get_header('Authorization') is None


def test_download_atomic_checksum_dedup_and_cache(tmp_path,monkeypatch):
    payload=image(tmp_path).read_bytes();calls=[];real_replace=library.os.replace;published=[]
    def replace(a,b):
        if 'objects' in Path(b).parts:
            assert not Path(b).exists() and library.inspect_media(a)['type']=='image';published.append(str(b))
        return real_replace(a,b)
    monkeypatch.setattr(library.os,'replace',replace)
    def get(url):calls.append(url);return Response(payload)
    with library.Library(tmp_path/'library') as lib:
        a=lib.download(metadata(),get);b=lib.download(metadata(),lambda u:pytest.fail('cached URL downloaded'))
        other=metadata('two',checksum=a['checksum'])
        c=lib.download(other,lambda u:pytest.fail('known checksum downloaded'))
        assert a['checksum']==b['checksum']==c['checksum'] and len(published)==1 and len(calls)==1
        assert len(lib.records('Photographer',kind='image'))==2
        assert lib.records(orientation='landscape')
        Path(a['local_path']).write_bytes(b'corrupt')
        with pytest.raises(ValueError,match='corupt'):lib.download(metadata(),get)


def test_download_interruption_recovery_and_invalid_mime(tmp_path):
    payload=image(tmp_path).read_bytes()
    with library.Library(tmp_path/'library') as lib:
        with pytest.raises(ValueError,match='incomplet'):lib.download(metadata(),lambda u:Response(payload[:30],size=len(payload)))
        assert not lib.records() and len(list((lib.root/'attempts').glob('*/payload.part')))==1
        assert json.loads(next((lib.root/'attempts').glob('*/download.json')).read_text())['phase']=='failed'
        with pytest.raises(ValueError,match='Content-Type'):lib.download(metadata(),lambda u:Response(payload,mime='text/html'))
        with pytest.raises(ValueError,match='Checksum'):lib.download(metadata(checksum='0'*64),lambda u:Response(payload))
        asset=lib.download(metadata(),lambda u:Response(payload));assert lib.check(asset).is_file()
        assert len(list((lib.root/'attempts').glob('*/payload.part')))>=2  # diagnostics retained
        with pytest.raises(ValueError,match='MIME real'):lib.download(metadata('exe'),lambda u:Response(b'MZ'+b'\0'*100,mime='image/png'))


def test_image_limits_and_path_traversal_name(tmp_path):
    p=image(tmp_path);a=metadata('../../evil.exe')
    with library.Library(tmp_path/'library') as lib:
        asset=lib.download(a,lambda u:Response(p.read_bytes()))
        assert Path(asset['local_path']).is_relative_to(lib.root/'objects')
        assert Path(asset['local_path']).name==asset['checksum']+'.png'
        fake=tmp_path/'fake.jpg';fake.write_text('<script>evil()</script>')
        with pytest.raises(ValueError,match='MIME real'):lib.ingest(fake)


def setup_three(material,tmp_path):
    p,m,c,original,words=material;content.import_alignment(p,words,'constructed fixture')
    images=[image(tmp_path,x) for x in ['red','blue','green']];bounds=[0,m['frames']//3,2*m['frames']//3,m['frames']]
    plan=tmp_path/'plan.json';core.write(plan,dict(scenes=[dict(id=f's{i}',start=a,end=b,path=str(images[i]),kind='image',anchor=['Ștefan','citește.','Măriuca'][i],motion='none',transition='cut') for i,(a,b) in enumerate(zip(bounds,bounds[1:]))]))
    video.import_scenes(p,plan)
    for i,img in enumerate(images):scenes.select(p,f's{i}',path=img,approve=True,library_root=tmp_path/'library')
    return p,m,c,images


def test_search_assisted_queries_ranking_and_selection(material,tmp_path,monkeypatch):
    p,m,c,img,_=material
    results=[metadata(str(i),width=300+i*500) for i in range(4)]
    monkeypatch.setattr(providers.Commons,'search',lambda *a,**k:results)
    result=scenes.search(p,'initial',['commons'],'Romania',library_root=tmp_path/'library') if m['scenes'][0]['id']=='initial' else scenes.search(p,m['scenes'][0]['id'],['commons'],'Romania',library_root=tmp_path/'library')
    _,current=core.load(p);assert result['mode']=='assisted' and len(result['candidates'])==4 and not current['scenes'][0].get('selected_asset')
    query=scenes.queries('Nicolae Ceaușescu în România în 1989. Partidul și revoluția.')
    assert '1989' in query['period'] and query['query_ro'] and query['query_en'] and query['persons']
    unknown=metadata('bad',license=providers.UNKNOWN,provenance_complete=False)
    ranked=scenes.rank([unknown,*results],'Romania');assert not ranked[-1]['auto_eligible']
    same=results[0];ranked=scenes.rank(results,'Romania',previous=same['candidate_id']);assert ranked[0]['candidate_id']!=same['candidate_id']


def test_license_unknown_explicit_approval_and_undo_overrides(material,tmp_path):
    p,m,c,img,_=material;identifier=m['scenes'][0]['id']
    with library.Library(tmp_path/'library') as lib:
        a=lib.ingest(img,metadata(license=providers.UNKNOWN,provenance_complete=False));b=lib.ingest(image(tmp_path,'blue'),metadata('blue'))
    with pytest.raises(ValueError,match='LICENSE_UNKNOWN'):scenes.select(p,identifier,a['asset_id'],library_root=tmp_path/'library')
    scenes.select(p,identifier,a['asset_id'],approve=True,allow_unknown=True,library_root=tmp_path/'library')
    scenes.select(p,identifier,b['asset_id'],profile='portrait',approve=True,library_root=tmp_path/'library')
    _,current=core.load(p);s=current['scenes'][0]
    assert scenes.effective(s,'portrait')['asset']['sha256']==b['checksum']
    assert scenes.effective(s,'landscape')['asset']['sha256']==a['checksum']
    scenes.select(p,identifier,restore=True)
    _,restored=core.load(p);assert not restored['scenes'][0]['profile_overrides']
    credit=scenes.credits(p);assert 'Photographer' in json.dumps(credit) and (p.parent/'CREDITS.md').is_file()
    with pytest.raises(ValueError,match='AUTO'):scenes.select(p,identifier,auto=True,library_root=tmp_path/'library')
    with pytest.raises(ValueError,match='Audio extern'):scenes.select(p,identifier,settings={'video':{'audio_enabled':True}})


def test_partial_rerender_offline_provenance_split_merge(material,tmp_path,monkeypatch):
    p,m,c,images=setup_three(material,tmp_path)
    monkeypatch.setattr(http,'open_url',lambda *a,**k:pytest.fail('render network access'))
    monkeypatch.setattr(socket,'create_connection',lambda *a,**k:pytest.fail('network access'))
    _,initial=core.load(p);alignment=core.key(initial['alignment']);timeline=core.key(initial['timeline'])
    first=video.render(p,{'custom':[320,240]},c,subtitles='classic',output_root=tmp_path/'before')
    run=tmp_path/'work/media/runs'/first['run_id'];clips=sorted((run/'custom').glob('scene-*.mkv'));before={f.name:(core.sha(f),f.stat().st_mtime_ns) for f in clips};master=core.sha(run/'master.wav')
    scenes.select(p,'s1',path=image(tmp_path,'yellow'),approve=True,library_root=tmp_path/'library')
    real_generate=video.asset_render.generate;generated=[]
    def generate(document,scene,*args):generated.append(scene['id']);return real_generate(document,scene,*args)
    monkeypatch.setattr(video.asset_render,'generate',generate)
    monkeypatch.setattr(video,'assemble',lambda *a,**k:pytest.fail('unchanged audio assembled'))
    result=video.render(p,{'custom':[320,240]},c,subtitles='classic',resume_run=run.name,rerender_changed=True,output_root=tmp_path/'after')
    assert generated==['s1'] and result['outputs'][0]['verification']['full_decode']
    assert core.sha(clips[0])==before[clips[0].name][0] and clips[0].stat().st_mtime_ns==before[clips[0].name][1]
    assert core.sha(clips[2])==before[clips[2].name][0] and clips[2].stat().st_mtime_ns==before[clips[2].name][1]
    assert core.sha(clips[1])!=before[clips[1].name][0] and list((run/'custom/revisions').glob('*/scene-00001.mkv'))
    assert core.sha(run/'master.wav')==master
    _,current=core.load(p);assert core.key(current['alignment'])==alignment and core.key(current['timeline'])==timeline
    assert (tmp_path/'after/fixture/custom/credits.json').is_file()
    reused=video.render(p,{'custom':[320,240]},c,subtitles='classic',resume_run=run.name,output_root=tmp_path/'after')
    assert reused['outputs'][0]['already_complete']
    _,_,plan=derive.split_plan(p,parts=2);children=derive.apply_split(p,plan,'assets-part');merged=derive.merge(children,'assets-joined')
    _,joined=core.load(merged);assert all(s.get('selected_asset',{}).get('checksum') for s in joined['scenes'])
    assert (Path(merged).parent/'credits.json').is_file()
    for child in children:
        _,cm=core.load(child);assert cm['scenes'] and all(0<=s['start']<s['end']<=cm['frames'] for s in cm['scenes'])


@pytest.mark.parametrize('policy',['loop','freeze'])
def test_video_interval_and_external_audio_muted(material,tmp_path,policy):
    p,m,c,img,_=material;identifier=m['scenes'][0]['id'];clip=tmp_path/'external.mp4'
    core.ff(['-f','lavfi','-i','color=c=blue:s=320x240:r=30:d=1','-f','lavfi','-i','sine=frequency=1000:sample_rate=22050:duration=1','-t','1','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-threads','2',clip])
    scenes.select(p,identifier,path=clip,approve=True,library_root=tmp_path/'library')
    scenes.select(p,identifier,settings={'video':{'source_start':.2,'source_end':.8},'visual':{'short_policy':policy,'fit':'cover','crop':[0,0,1,1]}})
    result=video.render(p,{'custom':[320,240]},c,output_root=tmp_path/policy)
    assert result['outputs'][0]['verification']['full_decode']
    out=result['outputs'][0]['path'];master=tmp_path/'work/media/runs'/result['run_id']/'master.wav'
    def pcm(path):
        import array
        r=subprocess.run([core.tool('ffmpeg'),'-v','error','-i',str(path),'-map','0:a:0','-f','f32le','-'],capture_output=True);assert r.returncode==0
        a=array.array('f');a.frombytes(r.stdout);return a
    a,b=pcm(master),pcm(out);assert len(b)>=len(a)
    dot=sum(x*y for x,y in zip(a,b));correlation=dot/math.sqrt(sum(x*x for x in a)*sum(y*y for y in b[:len(a)]))
    assert correlation>.98  # Project's 330 Hz fixture, never the external 1000 Hz tone.


def test_fallback_review_thumbnail_and_settings(material,tmp_path):
    p,m,c,img,_=material;identifier=m['scenes'][0]['id']
    core.write(tmp_path/'media.json',c)
    scenes.select(p,identifier,remove=True,approve=True,library_root=tmp_path/'library')
    scenes.select(p,identifier,settings={'visual':{'fit':'cover','focal_point':[.7,.4],'crop':[.1,.1,.9,.9],'zoom':1.1,'motion':'pan','pan':[.9,.5],'overlay':'Ștefan','title_overlay':'Titlu','subtitle_placement':'top'}})
    result=video.render(p,{'custom':[320,240]},c,output_root=tmp_path/'fallback');assert result['technical_status']=='passed'
    a=scenes.review(p,tmp_path/'review');assert Path(a['review']).is_file()
    thumbs=scenes.thumbnail(p,tmp_path/'thumbs',{'custom':[320,240]},c,text='Titlu',scene_id=identifier)
    assert len(thumbs)==1 and core.read(Path(thumbs[0]).with_suffix('.json'))['provenance']['provider']=='graphic'


def test_safe_range_resume_and_rate_limit(tmp_path):
    from urllib.error import HTTPError
    data=image(tmp_path).read_bytes();cut=len(data)//2
    class Interrupted(Response):
        def __init__(self):
            super().__init__(data);self.headers.update({'ETag':'"stable"','Accept-Ranges':'bytes'});self.calls=0
        def read(self,n=-1):
            self.calls+=1
            if self.calls==1:return data[:cut]
            raise OSError('connection interrupted')
    with library.Library(tmp_path/'library') as lib:
        with pytest.raises(OSError):lib.download(metadata(),lambda url:Interrupted())
        assert not lib.records()
        def resume(url,headers):
            assert headers=={'Range':f'bytes={cut}-','If-Range':'"stable"'}
            result=Response(data[cut:]);result.status=206;result.headers.update({'Content-Range':f'bytes {cut}-{len(data)-1}/{len(data)}','ETag':'"stable"'})
            return result
        asset=lib.download(metadata(),resume);assert asset['checksum']==core.sha(image(tmp_path))
        def limited(url):raise HTTPError(url,429,'rate limit',{'Retry-After':'60'},None)
        with pytest.raises(HTTPError):lib.download(metadata('limited'),limited)
        with pytest.raises(ValueError,match='cooldown'):lib.download(metadata('limited-again'),lambda u:pytest.fail('rate limit bypass'))


def test_auto_known_license_and_sequence(material,tmp_path):
    p,m,c,img,_=material;identifier=m['scenes'][0]['id']
    with library.Library(tmp_path/'library') as lib:
        a=lib.ingest(img,metadata('one'));b=lib.ingest(image(tmp_path,'blue'),metadata('two'))
    _,current=core.load(p);current['scenes'][0]['alternatives']=[dict(a,candidate_id='a',provenance_complete=True),dict(b,candidate_id='b',provenance_complete=True)];core.write(p,current)
    scenes.select(p,identifier,auto=True,approve=True,library_root=tmp_path/'library')
    _,current=core.load(p);assert current['scenes'][0]['selected_asset']['checksum'] in (a['checksum'],b['checksum'])
    plan=tmp_path/'sequence.json';core.write(plan,[dict(asset_id=a['asset_id'],frames=m['frames']//2),dict(asset_id=b['asset_id'],frames=m['frames']-m['frames']//2)])
    before=core.key(current['timeline']);result=scenes.sequence(p,identifier,plan,approve=True,library_root=tmp_path/'library')
    _,current=core.load(p);assert len(result['scenes'])==2 and core.key(current['timeline'])==before
    assert result['scenes'][0]['end']==result['scenes'][1]['start']
    assert not scenes.rank([metadata(license='CC BY-NC-ND 4.0')],'q')[0]['auto_eligible']


def test_renderer_rejects_remote_playlist(tmp_path):
    p=tmp_path/'playlist.m3u8';p.write_text('#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=10000\nhttps://example.org/remote.m3u8\n')
    with pytest.raises(ValueError,match='whitelist|Protocol'):video.probe(p)


def test_commons_video_uses_actual_transcode_not_original():
    payload={'query':{'pages':{'1':{'pageid':1,'title':'File:Protest.webm','videoinfo':[dict(url='https://images.example/original.webm',mime='video/webm',width=1280,height=720,descriptionurl='https://commons.wikimedia.org/wiki/File:Protest.webm',sha1='a'*40,extmetadata={},derivatives=[{'src':'https://images.example/original.webm','width':1280,'height':720},{'src':'//upload.wikimedia.org/wikipedia/commons/transcoded/protest.480p.webm','width':854,'height':480,'transcodekey':'480p.webm'}])]}}}}
    row=providers.Commons().search('protest','video',3,get=lambda url:payload)[0]
    assert row['download_url'].startswith('https://upload.wikimedia.org/')
    assert row['width']==854 and 'upstream_sha1' not in row
    assert row['original_upstream_sha1']=='a'*40


def test_split_preserves_portrait_video_interval_over_image_default(material,tmp_path):
    p,m,c,img,_=material;identifier=m['scenes'][0]['id'];clip=tmp_path/'portrait.mp4'
    core.ff(['-f','lavfi','-i','testsrc2=s=160x120:r=30:d=3','-an','-c:v','libx264','-threads','2',clip])
    scenes.select(p,identifier,path=img,approve=True,library_root=tmp_path/'library')
    scenes.select(p,identifier,path=clip,profile='portrait',approve=True,library_root=tmp_path/'library')
    scenes.select(p,identifier,profile='portrait',settings={'video':{'source_start':.2,'source_end':2.5}})
    _,current=core.load(p);cut=current['frames']//2
    intervals=tmp_path/'intervals.json';core.write(intervals,{'intervals':[[cut,current['frames']]]})
    _,_,plan=derive.split_plan(p,mode='extract',intervals=[[cut,current['frames']]])
    children=derive.apply_split(p,plan,'portrait-child')
    _,child=core.load(children[0]);effective=scenes.effective(child['scenes'][0],'portrait')
    assert effective['kind']=='video' and effective['audio_enabled'] is False
    assert effective['source_start']==pytest.approx(.2+cut/current['sample_rate'])
    assert effective['selected_asset']['provider']=='local'


def test_import_rejects_declared_checksum_mismatch(tmp_path):
    source = image(tmp_path)
    with library.Library(tmp_path/'library') as lib:
        with pytest.raises(ValueError, match='Checksum'):
            lib.ingest(source, metadata(checksum='0'*64))
        assert not lib.records()
        asset = lib.ingest(source, metadata(checksum=core.sha(source)))
        assert asset['checksum'] == core.sha(source)


def test_video_review_has_three_distinct_frames_and_reuses_preview(material, tmp_path, monkeypatch):
    p, m, c, img, _ = material
    core.write(tmp_path/'media.json', c)
    clip = tmp_path/'preview.mp4'
    core.ff(['-f', 'lavfi', '-i', 'testsrc2=s=160x120:r=30:d=1',
             '-an', '-c:v', 'libx264', '-threads', '2', clip])
    with library.Library(tmp_path/'library') as lib:
        asset = lib.ingest(clip, metadata('preview'))
    _, current = core.load(p)
    current['scenes'][0]['alternatives'] = [dict(asset, candidate_id='preview')]
    core.write(p, current)
    folder = tmp_path/'review'
    scenes.review(p, folder)
    preview = next(folder.glob('*-video.png'))
    with Image.open(preview) as im:
        assert im.size == (780, 180)
        assert im.crop((0, 0, 256, 144)).tobytes() != im.crop((260, 0, 516, 144)).tobytes()
    text = (folder/'scene-review.md').read_text()
    assert 'Preview frames (s): [0.1, 0.5, 0.9]' in text
    assert preview.name in text and 'CC BY 4.0' in text
    before = (core.sha(preview), preview.stat().st_mtime_ns)
    monkeypatch.setattr(core, 'ff', lambda *a, **k: pytest.fail('cached preview regenerated'))
    scenes.review(p, folder)
    assert before == (core.sha(preview), preview.stat().st_mtime_ns)
