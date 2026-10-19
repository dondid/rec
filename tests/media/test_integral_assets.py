"""Focused integral workflow contracts; no network, synthesis or video renders."""
from pathlib import Path
from PIL import Image
import pytest
from test_media import material
from rec_media import core, asset_library, asset_scenes as scenes, asset_providers as providers


def make_asset(tmp_path, lib, color, identifier):
    path=tmp_path/(color+'.png');Image.new('RGB',(320,240),color).save(path)
    meta=providers.candidate('commons',identifier,'Romania monument','https://example.org/'+identifier,'https://example.org/wiki/'+identifier,'Author','CC BY 4.0','https://creativecommons.org/licenses/by/4.0/')
    return lib.ingest(path,meta)


def test_library_first_never_requests_http_with_three_local_candidates(material,tmp_path,monkeypatch):
    p,m,c,*_=material
    with asset_library.Library(tmp_path/'library') as lib:
        for i,color in enumerate(['red','green','blue']):make_asset(tmp_path,lib,color,str(i))
    monkeypatch.setattr(providers.Commons,'search',lambda *a,**k:pytest.fail('unnecessary HTTP'))
    result=scenes.search(p,m['scenes'][0]['id'],['commons'],'Romania',library_root=tmp_path/'library')
    assert len(result['candidates'])==3 and result['retrieval']==[dict(provider='library',count=3)]
    _,saved=core.load(p);assert not saved['scenes'][0].get('selected_asset')


def test_credits_only_effective_profile_and_thumbnail_sources(material,tmp_path):
    p,m,c,*_=material;identifier=m['scenes'][0]['id'];core.write(tmp_path/'media.json',c)
    with asset_library.Library(tmp_path/'library') as lib:
        a=make_asset(tmp_path,lib,'red','one');b=make_asset(tmp_path,lib,'blue','two');unused=make_asset(tmp_path,lib,'green','unused')
    scenes.select(p,identifier,a['asset_id'],approve=True,library_root=tmp_path/'library')
    scenes.select(p,identifier,b['asset_id'],profile='portrait',approve=True,library_root=tmp_path/'library')
    rows=scenes.credits(p,tmp_path/'credits',profiles=['portrait'])['credits']
    assert len(rows)==1 and rows[0]['asset']['checksum']==b['checksum']
    assert rows[0]['profile']=='portrait' and unused['checksum'] not in str(rows)
    scenes.thumbnail(p,tmp_path/'thumb',{'portrait':[320,480]},c,text='Titlu',scene_id=identifier)
    credits=core.read(tmp_path/'thumb/credits.json')
    assert len(credits['credits'])==1 and credits['credits'][0]['asset']['checksum']==b['checksum']
    assert a['checksum'] not in str(credits) and unused['checksum'] not in str(credits)


def test_review_manifest_status_and_separate_profiles(material,tmp_path):
    p,m,c,*_=material;core.write(tmp_path/'media.json',c);identifier=m['scenes'][0]['id']
    with asset_library.Library(tmp_path/'library') as lib:
        a=make_asset(tmp_path,lib,'red','one')
    scenes.select(p,identifier,a['asset_id'],approve=True,library_root=tmp_path/'library')
    scenes.select(p,identifier,settings={'review_status':'NEEDS_REVIEW','review_note':'No human decision yet.'})
    result=scenes.review(p,tmp_path/'review');row=core.read(result['manifest'])['scenes'][0]
    assert row['status']=='NEEDS_REVIEW' and row['review_required']
    assert row['query_ro'] and row['query_en'] and row['duration_seconds']>0
    assert set(row['profiles'])=={'landscape','portrait'} and row['orientation']=='landscape'
    assert Path(row['selected_preview']).is_file()
    with pytest.raises(ValueError,match='review_status'):scenes.select(p,identifier,settings={'review_status':'PASSED'})


def test_rejected_editorial_scene_blocks_even_plan_only(material):
    from rec_media import video
    p,m,c,*_=material
    scenes.select(p,m['scenes'][0]['id'],settings={'review_status':'REJECTED'})
    with pytest.raises(ValueError,match='rejected'):
        video.render(p,{'custom':[320,240]},c,plan_only=True)


def test_cli_queries_preserves_explicit_ro_en_overrides(material):
    from rec_media import cli
    p,m,c,*_=material
    core.write(p.parents[2]/'media.json',c)
    _,current=core.load(p)
    current['scenes'][0]['curated_query']={'query_ro':'Clădire istorică','query_en':'historic building'}
    core.write(p,current)
    args=cli.parser().parse_args(['assets','queries',str(p),'--scene',m['scenes'][0]['id']])
    result=cli.execute(args)
    assert result['query_ro']=='Clădire istorică' and result['query_en']=='historic building'
    assert result['query_override_source']=='scene.curated_query'
