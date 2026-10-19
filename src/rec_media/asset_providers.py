"""Retrieval adapters only. No selection, renderer access or implicit downloads."""
import html
import os
import re
from urllib.parse import urlencode
from . import asset_http
from .core import key

UNKNOWN = 'LICENSE_UNKNOWN'


def clean(value):
    return html.unescape(re.sub(r'<[^>]*>', ' ', str(value or ''))).strip()


def candidate(provider, identifier, title, url, source, creator='', license=None, license_url='', **more):
    license = clean(license)
    if license.lower() in ('', 'unknown', 'none', 'copyrighted'):
        license = UNKNOWN
    result = dict(candidate_id=key([provider, str(identifier)])[:24], provider=provider,
                  provider_id=str(identifier), title=clean(title), download_url=url,
                  source_url=source, creator=clean(creator), license=license,
                  license_url=license_url or '', attribution=clean(more.pop('attribution', '')),
                  type='image', width=0, height=0, duration=None)
    result.update(more)
    width, height = result['width'], result['height']
    result.update(local_path=None, checksum=None, status='proposed', ranking=None,
                  dimensions=[width, height], orientation=(
                      'landscape' if width > height else 'portrait' if height > width else 'square'
                  ) if width and height else None)
    if not result['attribution']:
        result['attribution'] = f"{result['title']} — {result['creator'] or 'creator unknown'} — {license} — {source}"
    result['provenance_complete'] = bool(source and creator and license != UNKNOWN and license_url)
    return result


class Commons:
    name = 'commons'
    def search(self, query, kind='image', limit=8, get=None):
        get = get or asset_http.get_json
        mime = 'filetype:video' if kind == 'video' else 'filetype:bitmap'
        params = dict(action='query', format='json', generator='search', gsrsearch=f'{query} {mime}',
                      gsrnamespace=6, gsrlimit=min(limit, 30), prop='imageinfo',
                      iiprop='url|size|mime|extmetadata|sha1', iiurlwidth=1920)
        if kind=='video':params.update(prop='videoinfo',viprop='url|size|mime|extmetadata|derivatives|sha1');params.pop('iiprop',None)
        data = get('https://commons.wikimedia.org/w/api.php?' + urlencode(params))
        if data.get('error'):raise ValueError('Commons API: ' + str(data['error']))
        rows = []
        for page in data.get('query', {}).get('pages', {}).values():
            infos = page.get('videoinfo' if kind=='video' else 'imageinfo', [])
            if not infos:continue
            info = infos[0]; ext = info.get('extmetadata', {})
            field = lambda name: clean(ext.get(name, {}).get('value', ''))
            mime = info.get('mime', '')
            if kind == 'video' and not (mime.startswith('video/') or mime == 'application/ogg'):continue
            if kind == 'image' and mime not in ('image/jpeg', 'image/png', 'image/webp', 'image/gif'):continue
            row = candidate(self.name, page['pageid'], page['title'], info['url'], info.get('descriptionurl', ''),
                            field('Artist'), field('LicenseShortName'), field('LicenseUrl'),
                            width=info.get('width', 0), height=info.get('height', 0),
                            thumbnail_url=info.get('thumburl'), upstream_sha1=info.get('sha1'),
                            attribution='; '.join(filter(None, [field('Artist'), field('Credit'), field('Attribution'), field('LicenseShortName'), info.get('descriptionurl')])) )
            row['type'] = kind; row['mime'] = mime; row['query'] = query
            row['thumbnail_width']=info.get('thumbwidth');row['thumbnail_height']=info.get('thumbheight')
            if kind=='video':
                derivatives=[d for d in info.get('derivatives',[]) if d.get('src') and ('/transcoded/' in d['src'] or d.get('transcodekey')) and 320<=int(d.get('width',0))<=1280]
                if derivatives:
                    derivative=max(derivatives,key=lambda d:int(d.get('width',0)))
                    row.update(original_download_url=row['download_url'],download_url=('https:'+derivative['src'] if derivative['src'].startswith('//') else derivative['src']),rendition='provider video transcode',original_upstream_sha1=row.pop('upstream_sha1',None),width=int(derivative['width']),height=int(derivative.get('height',0)))
            rows.append(row)
        return rows[:limit]


class Openverse:
    name = 'openverse'
    def search(self, query, kind='image', limit=8, get=None):
        if kind != 'image':return []  # Openverse currently indexes images/audio, not video.
        get = get or asset_http.get_json
        data = get('https://api.openverse.org/v1/images/?' + urlencode(dict(q=query, page_size=min(limit, 30), mature='false')))
        return [candidate(self.name, item['id'], item.get('title'), item['url'], item.get('foreign_landing_url'),
                          item.get('creator'), ('CC ' + item.get('license', '') + ' ' + item.get('license_version', '')).strip() if item.get('license') else UNKNOWN,
                          item.get('license_url'), width=item.get('width') or 0, height=item.get('height') or 0,
                          thumbnail_url=item.get('thumbnail'), attribution=item.get('attribution'),
                          upstream_provider=item.get('provider'), tags=[x.get('name', '') for x in item.get('tags', [])], query=query)
                for item in data.get('results', []) if not item.get('mature')][:limit]


class Pexels:
    name = 'pexels'
    def search(self, query, kind='image', limit=8, get=None):
        token = os.environ.get('PEXELS_API_KEY')
        if not token:raise ValueError('Pexels opțional: PEXELS_API_KEY lipsește; cheia nu se salvează în proiect.')
        get = get or asset_http.get_json
        endpoint = 'videos/search' if kind == 'video' else 'search'
        data = get('https://api.pexels.com/v1/' + endpoint + '?' + urlencode(dict(query=query, per_page=min(limit, 30))), {'Authorization': token})
        result = []
        for item in data.get('videos' if kind == 'video' else 'photos', []):
            creator = item.get('user', {}).get('name') if kind == 'video' else item.get('photographer')
            if kind == 'video':
                files = [f for f in item.get('video_files', []) if f.get('file_type') == 'video/mp4' and f.get('width') and f['width'] <= 1920]
                if not files:continue
                selected = max(files, key=lambda x: x['width'] * x['height']); url = selected['link']
            else:selected = item; url = item['src']['original']
            row = candidate(self.name, item['id'], item.get('alt') or f'Pexels {item["id"]}', url, item['url'], creator,
                            'Pexels License', 'https://www.pexels.com/license/', width=selected['width'], height=selected['height'],
                            thumbnail_url=item.get('image') if kind == 'video' else item['src'].get('medium'),
                            attribution=f"{creator} on Pexels — {item['url']} — Photos/videos provided by Pexels https://www.pexels.com", query=query)
            row.update(type=kind, duration=item.get('duration')); result.append(row)
        return result


PROVIDERS = {p.name: p for p in (Commons(), Openverse(), Pexels())}
