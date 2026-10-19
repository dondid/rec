"""Scene asset selection, editorial review and provenance, independent of TTS."""
from collections import Counter
from copy import deepcopy
import math
import os
from pathlib import Path
import re
import uuid
from PIL import Image, ImageDraw, ImageFont
from . import core, asset_providers, asset_library

UNKNOWN = asset_providers.UNKNOWN
MODES = ('manual', 'assisted', 'auto')
REVIEW_STATUSES = ('APPROVED', 'PROPOSED', 'NEEDS_REVIEW', 'FALLBACK', 'LICENSE_UNKNOWN', 'REJECTED')


def find(material, identifier):
    matches = [s for s in material['scenes'] if s.get('scene_id', s['id']) == identifier or s['id'] == identifier]
    if len(matches) != 1:raise ValueError('scene_id inexistent/ambiguu: ' + str(identifier))
    return matches[0]


def context(material, scene):
    words = (material.get('alignment') or {}).get('words', [])
    return ' '.join(w['spoken'] for w in words if scene['start'] <= w['start'] < scene['end']) or scene.get('context') or scene.get('anchor', '')


def queries(text):
    stop = set('care este sunt fost pentru dintre într acest această unei unui dacă când după înainte toate acestui numai foarte poate unde aceea ceva acestea spune făcut avem despre trebuie mai cum din sau iar dar că să și la cu în pe de un o nu se au am a e mă îți tot era ce ei vă îmi noi voi lor lui le îi mi'.split())
    words = re.findall(r'[\wȘȚĂÂÎșțăâî-]+', text)
    terms = [w for w in words if len(w) > 3 and w.casefold() not in stop]
    frequent = [w for w, _ in Counter(terms).most_common(7)]
    persons = list(dict.fromkeys(re.findall(r'\b[A-ZĂÂÎȘȚ][a-zăâîșț]+(?:\s+[A-ZĂÂÎȘȚ][a-zăâîșț]+){1,2}\b', text)))[:8]
    named_places=[p for p in persons if p.startswith(('Piața ','Palatul ','Catedrala ','Universitatea '))]
    persons=[p for p in persons if not p.startswith(('Piața ','Palatul ','Catedrala ','Universitatea ','În ','Partidul ','Statul ','Statului '))]
    organizations = list(dict.fromkeys(re.findall(r'\b[A-ZĂÂÎȘȚ]{2,8}\b', text)))[:8]
    places = [p for p in ['România','București','Brașov','Timișoara','Cluj','Iași','Europa','Rusia','Turcia'] if p.casefold() in text.casefold()]
    places += named_places
    periods = list(dict.fromkeys(re.findall(r'\b(?:18|19|20)\d{2}\b', text)))
    glossary = {'România':'Romania','București':'Bucharest','revoluție':'revolution','revoluția':'revolution','partid':'political party',
                'partidul':'political party','oameni':'people','comunism':'communism','comuniști':'communism','români':'Romanians',
                'drepturi':'civil rights','sistemul':'political system','muncă':'work','liderii':'political leaders','război':'war',
                'copii':'children','istorie':'history','Georgescu':'Georgescu','Ceaușescu':'Ceausescu','țară':'country'}
    ro = ' '.join((persons[:1] or places[:1]) + frequent[:5])[:180].strip() or text[:100]
    en_terms = [glossary.get(w, glossary.get(w.casefold(), w)) for w in (persons[:1] + places[:1] + frequent[:5]) if w in glossary or w.casefold() in glossary or w[:1].isupper()]
    if not en_terms:en_terms=['documentary']
    events=list(dict.fromkeys(re.findall(r'(?i)revoluți\w+(?:\s+din)?\s+\d{4}|protest\w*',text)))[:5]
    objects=[w for w in ['stradă','biserică','catedrală','telefon','steag','urnă'] if w in text.casefold()]
    return dict(query_ro=ro, query_en=' '.join(en_terms)[:180], query_alternative_1=' '.join(persons[:2] or organizations[:2] or frequent[:3]),
                query_alternative_2=' '.join(places + periods + frequent[:2]), persons=persons, places=places, events=events, period=periods,
                organizations=organizations, objects=objects, themes=frequent, visual_context=ro,
                method='lexical proposals and small RO/EN glossary; entities/translation require review')


def rank(candidates, query, size=(1920, 1080), duration=0, usage=None, previous=None):
    terms = set(re.findall(r'\w{3,}', query.casefold())); usage = usage or {}
    result = []
    for original in candidates:
        item = deepcopy(original); title = (item.get('title', '') + ' ' + ' '.join(item.get('tags', []))).casefold()
        overlap = sum(t in title for t in terms) / max(1, len(terms))
        width, height = item.get('width') or 0, item.get('height') or 0
        aspect = width / height if height else 0
        ratio = min(aspect, size[0]/size[1]) / max(aspect, size[0]/size[1]) if aspect else 0
        quality = min(1, width * height / (size[0] * size[1]))
        restricted=bool(re.search(r'(?i)(?:\bnc\b|\bnd\b|non.?commercial|no.?deriv)',item.get('license','')))
        allowed = item.get('license') != UNKNOWN and item.get('provenance_complete', False) and not restricted
        duration_fit = 0 if item.get('type') != 'video' else min(1, (item.get('duration') or 0)/max(duration, .01))
        repeats = usage.get(item.get('asset_id'), 0)
        repeated_neighbor = bool(previous and (item.get('checksum') or item['candidate_id']) == previous)
        components = dict(text=round(overlap*5, 4), resolution=round(quality, 4), aspect=round(ratio, 4),
                          license=2 if allowed else -20, duration=duration_fit, usage=-min(repeats, 4)*.4,
                          consecutive=-8 if repeated_neighbor else 0)
        item.update(rank_score=round(sum(components.values()), 4), rank_reason=components, auto_eligible=allowed,
                    ranking=dict(score=round(sum(components.values()), 4), components=components),
                    ranking_note='Text/geometry/license heuristic, not visual semantic understanding')
        result.append(item)
    return sorted(result, key=lambda x: (-x['rank_score'], x['candidate_id']))


def save(document, material):
    core.write(document, material)
    core.write(document.parent / 'scenes.json', dict(schema_version=1, scenes=material['scenes']))
    credits(document)


def search(value, scene_id, providers=('commons','openverse'), query=None, kind='image', limit=8, mode='assisted', library_root=None):
    if mode not in MODES:raise ValueError('Mod asset invalid.')
    if not 3 <= limit <= 30:raise ValueError('Limită candidați între 3 și 30.')
    document, material = core.load(value); scene = find(material, scene_id)
    proposed = queries(context(material, scene))
    proposed.update({k:v for k,v in scene.get('curated_query',{}).items() if k in ('query_ro','query_en')})
    selected_query = query or proposed['query_ro']
    found = {}; errors = []; retrieval = []
    for provider in providers:
        if provider not in asset_providers.PROVIDERS:raise ValueError('Provider necunoscut: ' + provider)
    with asset_library.Library(library_root) as library:
        for item in library.records(selected_query, kind):
            library.check(item)
            entry = dict(item, candidate_id=item.get('candidate_id') or item['asset_id'], provenance_complete=provenance_complete(item))
            found[entry['candidate_id']] = entry
        retrieval.append(dict(provider='library', count=len(found)))
        # Retrieval is bounded and sequential; a sufficient local shortlist needs no HTTP.
        for provider in providers:
            if len([a for a in found.values() if provenance_complete(a)]) >= 3:break
            if provider == 'pexels' and not os.environ.get('PEXELS_API_KEY'):
                retrieval.append(dict(provider=provider,status='BLOCKED_OPTIONAL'));continue
            try:
                entries=asset_providers.PROVIDERS[provider].search(selected_query, kind, limit)
                for item in entries:found.setdefault(item['candidate_id'],item)
                retrieval.append(dict(provider=provider,count=len(entries)))
            except Exception as error:errors.append(dict(provider=provider, error=str(error)))
        candidates = rank(list(found.values()), selected_query, duration=(scene['end']-scene['start'])/material['sample_rate'], usage=library.usage_counts())
    old = {a['candidate_id']:a for a in scene.get('alternatives', [])}
    # Keep downloaded origins and previous search alternatives, including video.
    for item in candidates:
        if item['candidate_id'] in old:
            item.update({k:v for k,v in old[item['candidate_id']].items() if k in ('local_path','checksum','asset_id','downloaded_at','duration')})
        old[item['candidate_id']] = item
    scene.update(asset_mode=mode, discovery_queries=proposed, alternatives=list(old.values()))
    scene.setdefault('discovery_history', []).append(dict(created_utc=core.now(), query=selected_query, providers=list(providers), retrieval=retrieval, type=kind, errors=errors, count=len(candidates)))
    if mode == 'auto':scene['recommended_candidate'] = next((a['candidate_id'] for a in candidates if a['auto_eligible']), None)
    save(document, material)
    return dict(scene=scene_id, mode=mode, queries=proposed, query_used=selected_query, candidates=candidates, errors=errors,
                retrieval=retrieval, minimum_three_available=len(candidates)>=3, technical_status='passed' if candidates else 'partial')


def provenance_complete(asset):
    return bool(asset.get('provider') and asset.get('source_url') and asset.get('creator') and asset.get('license_url') and asset.get('license') not in (None, '', UNKNOWN, 'unknown'))


def effective(scene, profile=None):
    """Normalize additive fields for rendering; leave legacy scenes byte-for-byte."""
    if not scene.get('asset_schema'):return deepcopy(scene)
    result = deepcopy(scene)
    if profile:result.update(deepcopy(scene.get('profiles',{}).get(profile,{})))
    override = result.get('profile_overrides', {}).get(profile, {}) if profile else {}
    selected = override.get('selected_asset', result.get('selected_asset'))
    if selected:
        result['selected_asset'] = selected; result['kind'] = selected['type']
        result['asset'] = dict(path=selected['local_path'], sha256=selected['checksum'])
    visual = dict(result.get('visual', {})); visual.update(override.get('visual', {}))
    result.update({k:v for k,v in visual.items() if k not in ('focal_point',)})
    result['focal'] = visual.get('focal_point', result.get('focal', [.5,.5]))
    video = dict(result.get('video', {})); video.update(override.get('video', {})); result.update(video)
    result['audio_enabled'] = False
    return result


def validate_visual(visual):
    allowed={'fit','focal_point','crop','zoom','pan','motion','motion_amount','transition','overlay','title_overlay','subtitle_placement','short_policy'}
    if set(visual)-allowed:raise ValueError('Control vizual necunoscut: '+str(set(visual)-allowed))
    if 'motion_amount' in visual and (type(visual['motion_amount']) not in (int,float) or not math.isfinite(visual['motion_amount']) or not 0<=visual['motion_amount']<=.15):raise ValueError('motion_amount invalid.')
    if visual.get('fit', 'contain') not in ('contain', 'cover'):raise ValueError('fit invalid.')
    if visual.get('motion', 'none') not in ('none','zoom_in','zoom_out','pan'):raise ValueError('motion invalid.')
    if visual.get('transition', 'cut') not in ('cut','crossfade'):raise ValueError('transition invalid.')
    for field in ['focal_point', 'pan']:
        if field in visual and (len(visual[field]) != 2 or any(type(x) not in (int,float) or not math.isfinite(x) or not 0 <= x <= 1 for x in visual[field])):raise ValueError(field + ' invalid.')
    if 'crop' in visual:
        a,b,c,d = visual['crop']
        if not all(type(x) in (int,float) and math.isfinite(x) for x in (a,b,c,d)) or not 0<=a<c<=1 or not 0<=b<d<=1:raise ValueError('crop normalizat invalid.')
    if 'zoom' in visual and (type(visual['zoom']) not in (int,float) or not 1 <= visual['zoom'] <= 4):raise ValueError('zoom invalid.')
    for field in ['overlay', 'title_overlay']:
        if field in visual and visual[field] is not None and not isinstance(visual[field], str):raise ValueError(field+' trebuie să fie text.')
    if visual.get('subtitle_placement', 'bottom') not in ('bottom','top'):raise ValueError('subtitle_placement invalid.')
    if visual.get('short_policy', 'error') not in ('error','loop','freeze'):raise ValueError('short_policy invalid; alternativă/secvență/fallback prin selecție explicită.')


def snapshot(scene):
    return {k:deepcopy(scene.get(k)) for k in ['asset','kind','selected_asset','profile_overrides','video','visual','status','approval_status','review_status','review_note','review_required']}


def upgrade(scene, material, document):
    if scene.get('asset_schema'):return
    scene.update(asset_schema=1, scene_id=scene['id'], context=context(material, scene), status='proposed',
                 video=dict(source_start=scene.get('source_start',0), source_end=None, audio_enabled=False),
                 visual={k:deepcopy(scene[k]) for k in ('fit','motion','motion_amount','transition') if k in scene},
                 alternatives=scene.get('alternatives', []), profile_overrides={})
    scene['visual']['focal_point'] = scene.get('focal', [.5,.5])
    for name,settings in scene.get('profiles',{}).items():
        values=deepcopy(settings)
        if 'focal' in values:values['focal_point']=values.pop('focal')
        scene['profile_overrides'][name]={'visual':values}
    if scene.get('asset'):
        asset=scene['asset']
        scene['selected_asset']=dict(type=scene['kind'],local_path=str(core.resolve(document,asset['path'])),checksum=asset['sha256'],provider='local',source_url='',creator='local source',license=asset.get('license',UNKNOWN),license_url='',attribution=asset.get('provenance','local source'),downloaded_at=None)


def select(value, scene_id, candidate_id=None, path=None, profile=None, approve=False, allow_unknown=False,
           restore=False, remove=False, settings=None, library_root=None, auto=False):
    document, material = core.load(value); scene = find(material, scene_id)
    if profile and profile not in ('landscape','portrait','custom','square'):raise ValueError('Profil invalid.')
    upgrade(scene, material, document)
    previous = snapshot(scene)
    if restore:
        saved = scene.get('previous_selection')
        if not saved:raise ValueError('Nu există previous_selection.')
        for k,v in saved.items():
            if v is None:scene.pop(k,None)
            else:scene[k]=deepcopy(v)
    elif remove:
        with asset_library.Library(library_root) as library:
            folder=library.root/'generated';folder.mkdir(exist_ok=True);fallback=folder/(uuid.uuid4().hex+'.png')
            image=Image.new('RGB',(1280,720),'#24556a');draw=ImageDraw.Draw(image)
            draw.text((50,50),f"Fallback grafic — {scene_id}",font=ImageFont.truetype(core.config()['font'],28),fill='white');image.save(fallback)
            asset=library.ingest(fallback,dict(provider='graphic',creator='REC',license='original graphic',attribution='REC local graphic fallback'))
        attach(scene, asset, profile, approve, allow_unknown)
    elif candidate_id or path or auto:
        with asset_library.Library(library_root) as library:
            if path:asset=library.ingest(path,dict(provider='local',creator='user supplied',license=UNKNOWN,attribution='Local user supplied asset; rights not inferred'))
            else:
                alternatives=scene.get('alternatives', [])
                if auto:
                    previous_asset=None
                    index=material['scenes'].index(scene)
                    if index:
                        prev=effective(material['scenes'][index-1],profile);previous_asset=(prev.get('selected_asset') or {}).get('checksum')
                    choices=rank(alternatives, scene.get('discovery_queries',{}).get('query_ro',scene.get('anchor','')),usage=library.usage_counts(),previous=previous_asset)
                    selected=next((a for a in choices if a['auto_eligible'] and a.get('asset_id')),None)
                    if not selected:raise ValueError('AUTO: niciun candidat descărcat cu provenance/licență determinabilă.')
                else:selected=next((a for a in alternatives if a['candidate_id']==candidate_id),None)
                if selected and selected.get('asset_id'):asset=library.get(selected['asset_id'])
                elif selected:raise ValueError('Candidatul trebuie descărcat explicit înainte de selecție.')
                else:asset=library.get(candidate_id)
            attach(scene,asset,profile,approve,allow_unknown)
            library.use(material['id'],scene_id,profile,asset)
    if settings:
        allowed={'visual','video','status','end','start','review_status','review_note'}
        if set(settings)-allowed:raise ValueError('Câmpuri editabile: visual/video/status/start/end.')
        target=scene.setdefault('profile_overrides',{}).setdefault(profile,{}) if profile else scene
        if 'visual' in settings:
            visual=dict(target.get('visual',{}));visual.update(settings['visual']);validate_visual(visual);target['visual']=visual
        if 'video' in settings:
            video=dict(target.get('video',scene.get('video',{})));video.update(settings['video'])
            a,b=video.get('source_start',0),video.get('source_end')
            if type(a) not in (int,float) or not math.isfinite(a) or a<0 or (b is not None and (type(b) not in (int,float) or not math.isfinite(b) or b<=a)):raise ValueError('Interval video invalid.')
            if video.get('audio_enabled'):raise ValueError('Audio extern rămâne mut; mix extern este etapă separată.')
            video['audio_enabled']=False;target['video']=video
        if 'status' in settings:
            if settings['status'] not in ('proposed','approved','rejected'):raise ValueError('Status invalid.')
            scene['status']=settings['status'];scene['approval_status']='pending' if settings['status']=='proposed' else settings['status']
        if 'review_status' in settings:
            if settings['review_status'] not in REVIEW_STATUSES:raise ValueError('review_status invalid.')
            scene['review_status']=settings['review_status']
            scene['review_required']=settings['review_status'] not in ('APPROVED','REJECTED')
        if 'review_note' in settings:
            if not isinstance(settings['review_note'],str):raise ValueError('review_note trebuie să fie text.')
            scene['review_note']=settings['review_note']
        # Move only a shared visual boundary; never alter audio/timing words.
        if 'start' in settings or 'end' in settings:
            if profile:raise ValueError('Limitele vizuale sunt comune profilelor.')
            i=material['scenes'].index(scene)
            if 'start' in settings:
                a=settings['start']
                if not i or type(a) is not int or not material['scenes'][i-1]['start']<a<scene['end']:raise ValueError('Limită start invalidă.')
                material['scenes'][i-1]['end']=a;scene['start']=a
            if 'end' in settings:
                b=settings['end']
                if i+1==len(material['scenes']) or type(b) is not int or not scene['start']<b<material['scenes'][i+1]['end']:raise ValueError('Limită end invalidă.')
                scene['end']=b;material['scenes'][i+1]['start']=b
    scene['previous_selection']=previous;scene['current_selection']=snapshot(scene)
    scene.setdefault('selection_history',[]).append(dict(created_utc=core.now(),before=previous,after=snapshot(scene),action='restore' if restore else 'edit',manual_override=not auto))
    save(document,material)
    return dict(scene=scene,technical_status='passed')


def attach(scene, asset, profile, approve, allow_unknown):
    online=asset.get('provider') not in ('local','graphic','ai-local')
    unknown=asset.get('license') in (None,'',UNKNOWN,'unknown')
    if online and not provenance_complete(asset) and not (unknown and approve and allow_unknown and all(asset.get(k) for k in ['provider','source_url','creator','attribution'])):
        raise ValueError('Provenance incompletă / LICENSE_UNKNOWN: cere --approve --allow-unknown-license explicit; fără selecție AUTO.')
    selected={k:deepcopy(asset.get(k)) for k in ['type','local_path','provider','source_url','creator','license','license_url','attribution','checksum','downloaded_at','asset_id','orientation','dimensions','width','height','duration']}
    for field in ['generation','rendition','original_download_url']:
        if asset.get(field):selected[field]=deepcopy(asset[field])
    selected['unknown_license_explicitly_approved']=bool(unknown and approve and allow_unknown)
    if profile:scene.setdefault('profile_overrides',{}).setdefault(profile,{})['selected_asset']=selected
    else:
        scene['selected_asset']=selected;scene['asset']=dict(path=asset['local_path'],sha256=asset['checksum']);scene['kind']=asset['type']
    scene['status']='approved' if approve else 'proposed';scene['approval_status']='approved' if approve else 'pending'


def download(value, scene_id, identifier=None, all_candidates=False, library_root=None, rendition="original"):
    document, material=core.load(value);scene=find(material,scene_id);results=[];errors=[]
    choices=[a for a in scene.get('alternatives',[]) if all_candidates or a['candidate_id']==identifier]
    if not choices:raise ValueError('Candidat inexistent.')
    with asset_library.Library(library_root) as library:
        for item in choices:
            try:
                request=dict(item)
                if rendition=='thumbnail':
                    if item['type']!='image' or not item.get('thumbnail_url'):raise ValueError('Thumbnail rendition disponibil numai pentru imagini cu URL furnizat de provider.')
                    request.update(original_download_url=item['download_url'],download_url=item['thumbnail_url'],rendition='provider thumbnail',original_upstream_sha1=request.pop('upstream_sha1',None));request.pop('checksum',None)
                asset=library.download(request);item.update(asset);results.append(asset)
            except Exception as e:
                errors.append(dict(candidate_id=item['candidate_id'],error=str(e),http_status=getattr(e,'code',None)))
                if getattr(e,'code',None)==429 or 'cooldown' in str(e):break
    save(document,material)
    return dict(assets=results,errors=errors,technical_status='passed' if not errors else 'partial')


def credits(value, directory=None, profiles=None):
    document, material=core.load(value);folder=Path(directory or document.parent);records=[]
    for scene in material['scenes']:
        for profile in (profiles if profiles is not None else [None,*scene.get('profile_overrides',{})]):
            s=effective(scene,profile);asset=s.get('selected_asset')
            if not asset:
                asset=dict(s.get('asset',{}),type=s.get('kind'),provider='legacy-local',license=s.get('license',s.get('asset',{}).get('license',UNKNOWN)),attribution=s.get('asset',{}).get('provenance','local source'))
            records.append(dict(scene_id=scene.get('scene_id',scene['id']),start=scene['start'],end=scene['end'],sample_rate=material['sample_rate'],profile=profile or 'default',asset=asset))
    result=dict(material=material['id'],created_utc=core.now(),credits=records,license_clearance='not_a_legal_or_editorial_approval')
    core.write(folder/'credits.json',result)
    text=['# Credits', '', 'Licențele și drepturile se verifică înaintea publicării.', '']
    for row in records:
        a=row['asset'];text += [f"## {row['scene_id']} ({row['profile']})",'',f"{row['start']/row['sample_rate']:.3f}–{row['end']/row['sample_rate']:.3f} s",'',*[f"{k}: {a.get(k,'')}" for k in ['provider','source_url','creator','license','license_url','attribution','checksum','downloaded_at']],'']
    (folder/'CREDITS.md').write_text('\n'.join(text),encoding='utf-8')
    return result


def video_preview(asset, folder):
    """Three bounded frames, keyed by content; no network or source audio."""
    folder = Path(folder)
    duration = asset.get('duration')
    if not duration or not math.isfinite(duration) or duration <= 0:
        duration = asset_library.inspect_media(asset['local_path'])['duration']
    times = [duration * fraction for fraction in (.1, .5, .9)]
    preview = folder / (core.key(['video-preview-v1', asset['checksum']])[:24] + '-video.png')
    if not preview.exists():
        strip = Image.new('RGB', (780, 180), '#14232f')
        draw = ImageDraw.Draw(strip)
        font = ImageFont.truetype(core.config()['font'], 14)
        for index, timestamp in enumerate(times):
            frame = folder / (uuid.uuid4().hex + '-frame.png')
            core.ff(['-protocol_whitelist', 'file,pipe', '-threads', '2',
                     '-ss', str(timestamp), '-i', asset['local_path'], '-an',
                     '-vf', 'scale=256:144:force_original_aspect_ratio=decrease',
                     '-frames:v', '1', frame])
            with Image.open(frame) as image:
                strip.paste(image.convert('RGB'), (index * 260, 0))
            draw.text((index * 260 + 4, 150), f'{timestamp:.3f} s', font=font, fill='white')
        strip.save(preview)
    return preview, times


def selected_preview(document, scene, folder):
    """Sample selected intervals and profile framing, without rendering scene caches."""
    from .content import fit_image
    canvas=Image.new('RGB',(1000,460),'#14232f');draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype(core.config()['font'],16)
    for profile,size,x in [('landscape',(560,315),0),('portrait',(225,400),650)]:
        selected=effective(scene,profile);path=core.checked(document,selected['asset'])
        if selected['kind']=='video':
            start=selected.get('source_start',0);end=selected.get('source_end')
            if end is None:end=asset_library.inspect_media(path)['duration']
            frame=folder/(core.key(['selected-frame-v1',selected['asset']['sha256'],start,end])[:24]+'.png')
            if not frame.exists():core.ff(['-protocol_whitelist','file,pipe','-threads','2','-ss',str((start+end)/2),'-i',path,'-an','-vf','scale=960:960:force_original_aspect_ratio=decrease','-frames:v','1',frame])
            path=frame
        with Image.open(path) as source:
            source=source.convert('RGB');crop=selected.get('crop')
            if crop:source=source.crop(tuple(round(a*b) for a,b in zip(crop,[source.width,source.height]*2)))
            image=fit_image(source,size,selected.get('fit','contain'),selected.get('focal',[.5,.5]))
            canvas.paste(image,(x,30))
        draw.text((x,5),profile,font=font,fill='white')
    preview=folder/(core.key(scene.get('scene_id',scene['id']))[:24]+'-selected.jpg')
    canvas.save(preview);return preview


def review(value, directory):
    document, material=core.load(value);folder=Path(directory);folder.mkdir(parents=True,exist_ok=True)
    rows=['# Scene review','','Selecție: `./media scenes MATERIAL --scene SCENE_ID --select CANDIDATE_ID --approve`','']
    font=ImageFont.truetype(core.config()['font'],16);sheets=[];manifest=[]
    for scene in material['scenes']:
        identifier=scene.get('scene_id',scene['id']);candidates=scene.get('alternatives',[])
        count=max(1,len(candidates));canvas=Image.new('RGB',(1200,math.ceil(count/3)*390),'#14232f');draw=ImageDraw.Draw(canvas)
        rows += [f"## {identifier} — {scene['start']/material['sample_rate']:.3f}–{scene['end']/material['sample_rate']:.3f} s",'',context(material,scene),'',f"Status: {scene.get('status',scene.get('approval_status','pending'))}",f"Selected: {scene.get('selected_asset')}",'']
        status=scene.get('review_status','PROPOSED')
        profiles={name:effective(scene,name) for name in ('landscape','portrait')}
        selected=scene.get('selected_asset',{})
        entry=dict(scene_id=identifier,start=scene['start'],end=scene['end'],sample_rate=material['sample_rate'],duration_seconds=(scene['end']-scene['start'])/material['sample_rate'],context=context(material,scene),queries=scene.get('discovery_queries') or queries(context(material,scene)),selected_asset=selected,alternatives=candidates,provider=selected.get('provider'),source_url=selected.get('source_url'),creator=selected.get('creator'),license=selected.get('license'),asset_type=selected.get('type',scene.get('kind')),status=status,review_required=scene.get('review_required',status!='APPROVED'),review_note=scene.get('review_note',''),profiles=profiles)
        entry.update(query_ro=entry['queries']['query_ro'],query_en=entry['queries']['query_en'],orientation=selected.get('orientation'))
        preview=selected_preview(document,scene,folder);entry['selected_preview']=str(preview)
        manifest.append(entry)
        rows += [f'Review status: {status}',f"Duration: {entry['duration_seconds']:.3f} s",f"Note: {entry['review_note']}",f"Queries: {entry['queries']}",f'![Selected landscape / portrait]({preview.name})','']
        for i,a in enumerate(candidates):
            x=(i%3)*400;y=(i//3)*390;preview=None
            if a.get('local_path'):
                path=Path(a['local_path']);assert core.sha(path)==a['checksum'],'Asset preview corupt.'
                if a['type']=='video':
                    preview, times = video_preview(a, folder)
                    rows += [f'![Video {a["candidate_id"]}]({preview.name})',
                             f'Preview frames (s): {times}', '']
                    source=preview
                else:source=path
                with Image.open(source) as im:
                    im=im.convert('RGB');im.thumbnail((390,245));canvas.paste(im,(x+(400-im.width)//2,y))
            lines=[f"{i+1}. {a['candidate_id']}",a.get('title','')[:48],f"{a.get('width',0)}×{a.get('height',0)} {a.get('duration') or ''}",a.get('provider',''),a.get('license',UNKNOWN)]
            for j,line in enumerate(lines):draw.text((x+5,y+250+j*24),line,font=font,fill='white')
            rows += [f"### Candidat {i+1}: {a['candidate_id']}",*[f"{k}: {a.get(k,'')}" for k in ['title','provider','source_url','creator','license','license_url','attribution','rank_score','rank_reason','local_path']],'']
        sheet=folder/(core.key(identifier)[:24]+'.jpg');canvas.save(sheet);sheets.append(str(sheet));rows += [f'![{identifier}]({sheet.name})','']
    (folder/'scene-review.md').write_text('\n'.join(rows),encoding='utf-8')
    core.write(folder/'scene-review.json',dict(material=material['id'],created_utc=core.now(),scenes=manifest,editorial_review='not_reviewed',listening_review='not_reviewed'))
    return dict(review=str(folder/'scene-review.md'),manifest=str(folder/'scene-review.json'),contact_sheets=sheets,technical_status='passed')


def thumbnail(value,directory,profiles,config,text=None,scene_id=None,variant='panel',fmt='png'):
    from .content import fit_image,text_layer
    document,material=core.load(value);folder=Path(directory);folder.mkdir(parents=True,exist_ok=True)
    scene=find(material,scene_id) if scene_id else next((s for s in material['scenes'] if s.get('status')=='approved' or s.get('approval_status')=='approved'),None)
    if scene is None or (scene.get('status')!='approved' and scene.get('approval_status')!='approved'):raise ValueError('Thumbnail cere o scenă aprobată explicit.')
    text=text or material.get('thumbnail_text') or (material['titles'].get('selected') or {}).get('thumbnail_text')
    outputs=[];metadata=[]
    for profile,size in profiles.items():
        selected=effective(scene,profile);asset=core.checked(document,selected['asset']);source=asset
        if selected['kind']=='video':
            info=core.probe(asset);duration=float(info['format']['duration']);start=selected.get('source_start',0);end=selected.get('source_end') or duration
            source=folder/f'.{profile}-selected-frame.png';core.ff(['-protocol_whitelist','file,pipe','-threads','2','-ss',str((start+end)/2),'-i',asset,'-frames:v','1',source])
        with Image.open(source) as image:
            image=image.convert('RGB');crop=selected.get('crop')
            if crop:image=image.crop(tuple(round(a*b) for a,b in zip(crop,[image.width,image.height]*2)))
            background=fit_image(image,tuple(size),selected.get('fit',config['fit']),selected.get('focal',[.5,.5]))
        layer,layout=text_layer(tuple(size),text,config,variant);output=folder/f'{profile}-{variant}.{fmt}'
        if output.exists():raise ValueError('Thumbnail existent; folosește alt director.')
        Image.alpha_composite(background.convert('RGBA'),layer).convert('RGB').save(output,format='PNG' if fmt=='png' else 'JPEG')
        row=dict(material=material['id'],scene=scene.get('scene_id',scene['id']),profile=profile,size=size,text=text,layout=layout,sha256=core.sha(output),provenance=selected.get('selected_asset',selected['asset']),visual_review_status='not_reviewed')
        core.write(output.with_suffix('.json'),row);outputs.append(str(output));metadata.append(row)
    data=dict(material=material['id'],created_utc=core.now(),credits=[dict(scene_id=row['scene'],profile=row['profile'],asset=row['provenance']) for row in metadata],thumbnails=metadata,license_clearance='not_a_legal_or_editorial_approval')
    core.write(folder/'credits.json',data)
    (folder/'CREDITS.md').write_text('# Thumbnail credits\n',encoding='utf-8')
    with (folder/'CREDITS.md').open('a') as out:
        out.write('\n## Thumbnail sources\n\n')
        for row in metadata:out.write(f"{row['profile']}: {row['provenance']}\n\n")
    return outputs


def sequence(value,scene_id,plan,approve=False,allow_unknown=False,library_root=None):
    """Combine assets through explicit contiguous visual sub-scenes; audio is untouched."""
    document,material=core.load(value);original=find(material,scene_id);items=core.read(plan)
    if not isinstance(items,list) or len(items)<2:raise ValueError('Secvența cere minimum două assets cu durate în eșantioane.')
    if sum(item.get('frames',0) for item in items)!=original['end']-original['start']:raise ValueError('Secvența trebuie să acopere exact durata vizuală originală.')
    chunks=[];cursor=original['start'];identifier=original.get('scene_id',original['id'])
    with asset_library.Library(library_root) as library:
        for index,item in enumerate(items,1):
            frames=item['frames']
            if type(frames) is not int or frames<1:raise ValueError('frames invalid în secvență.')
            scene=deepcopy(original);upgrade(scene,material,document)
            scene.update(id=f'{identifier}-part-{index:03d}',scene_id=f'{identifier}-part-{index:03d}',start=cursor,end=cursor+frames)
            asset=library.get(item['asset_id']);attach(scene,asset,None,approve,allow_unknown)
            scene['visual'].update(item.get('visual',{}));validate_visual(scene['visual'])
            if 'video' in item:
                start=item['video'].get('source_start',0);end=item['video'].get('source_end')
                if not 0<=start or end is not None and end<=start:raise ValueError('Interval video invalid.')
                if item['video'].get('audio_enabled'):raise ValueError('Audio extern mut obligatoriu.')
                scene['video']={**item['video'],'audio_enabled':False}
            chunks.append(scene);cursor+=frames
    index=material['scenes'].index(original);material['scenes'][index:index+1]=chunks
    from .derive import map_scene_text
    map_scene_text(material)
    for scene in chunks:scene['context']=context(material,scene)
    if len({s['id'] for s in material['scenes']})!=len(material['scenes']):raise ValueError('ID-uri duplicate în secvență.')
    material['history'].append(dict(created_utc=core.now(),action='scene_asset_sequence',previous_scene=original,new_scenes=[s['id'] for s in chunks],audio_unchanged=True))
    save(document,material);return dict(scenes=chunks,technical_status='passed')
