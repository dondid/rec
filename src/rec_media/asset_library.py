"""Content-addressed local media library with a transactional searchable index."""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import sqlite3
import uuid
import time
from urllib.error import HTTPError
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode,unquote
from PIL import Image
from . import core, asset_http

MAX_BYTES = 256 * 1024 * 1024


def canonical_url(url):
    p=urlsplit(url)
    if p.hostname=='upload.wikimedia.org':
        query=urlencode([(k,v) for k,v in parse_qsl(p.query) if not k.startswith('utm_')])
        return urlunsplit((p.scheme,p.netloc,unquote(p.path),query,''))
    return url


def inspect_media(path, claimed_mime=None):
    """Require a real decodable supported raster/video, not its filename."""
    path = Path(path)
    if not 0 < path.stat().st_size <= MAX_BYTES:raise ValueError('Asset gol/prea mare.')
    with path.open('rb') as source:head = source.read(4096)
    formats = [('png', 'image/png', head.startswith(b'\x89PNG\r\n\x1a\n')),
               ('jpg', 'image/jpeg', head.startswith(b'\xff\xd8\xff')),
               ('webp', 'image/webp', head[:4] == b'RIFF' and head[8:12] == b'WEBP'),
               ('gif', 'image/gif', head[:6] in (b'GIF87a', b'GIF89a'))]
    image_format = next(((ext, mime) for ext, mime, match in formats if match), None)
    if image_format:
        ext, mime = image_format
        with Image.open(path) as image:
            if image.width * image.height > 40_000_000 or max(image.size) > 16384:raise ValueError('Rezoluție imagine excesivă.')
            if getattr(image, 'n_frames', 1) != 1:raise ValueError('Imagine animată: importă explicit drept video.')
            width, height = image.size; image.verify()
        with Image.open(path) as image:image.load()
        result = dict(type='image', width=width, height=height, duration=None, extension=ext, mime=mime)
    else:
        if head[4:8] == b'ftyp':ext, mime = 'mp4', 'video/mp4'
        elif head[:4] == b'\x1aE\xdf\xa3':ext, mime = ('mkv','video/x-matroska') if b'matroska' in head[:100] else ('webm','video/webm')
        elif head[:4] == b'OggS':ext, mime = 'ogv', 'video/ogg'
        else:raise ValueError('MIME real nepermis: numai imagini raster și video; fără SVG/HTML/executabile.')
        data = json.loads(core.run([core.tool('ffprobe'),'-v','error','-protocol_whitelist','file,pipe','-show_streams','-show_format','-of','json',path.resolve()])); streams = [s for s in data['streams'] if s['codec_type'] == 'video']
        if len(streams) != 1:raise ValueError('Video necesită un singur stream vizual.')
        v = streams[0]; duration = float(v.get('duration') or data['format'].get('duration', 0))
        if not math.isfinite(duration) or not 0 < duration <= 7200:raise ValueError('Durată video invalidă/excesivă.')
        if v['width'] * v['height'] > 20_000_000 or max(v['width'], v['height']) > 8192:raise ValueError('Rezoluție video excesivă.')
        core.ff(['-xerror', '-threads', '2', '-protocol_whitelist', 'file,pipe', '-i', path.resolve(), '-map', '0:v:0', '-f', 'null', '-'])
        result = dict(type='video', width=v['width'], height=v['height'], duration=duration, extension=ext, mime=mime,
                      external_audio_present=any(s['codec_type'] == 'audio' for s in data['streams']))
    if claimed_mime:
        claimed_mime = claimed_mime.partition(';')[0].lower().strip()
        allowed = {result['mime'], 'application/octet-stream'}
        if result['type'] == 'video':allowed |= {'video/x-matroska', 'application/ogg', 'video/quicktime'}
        if claimed_mime not in allowed:raise ValueError(f'Content-Type {claimed_mime} diferit de MIME real {result["mime"]}.')
    result['orientation'] = 'landscape' if result['width'] > result['height'] else ('portrait' if result['height'] > result['width'] else 'square')
    return result


class Library:
    def __init__(self, root=None):
        self.root = Path(root or core.ROOT / 'assets/library').resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.root / 'library.sqlite3')
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''CREATE TABLE IF NOT EXISTS assets (id TEXT PRIMARY KEY, checksum TEXT NOT NULL, url TEXT, document TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS asset_checksum ON assets(checksum);
            CREATE INDEX IF NOT EXISTS asset_url ON assets(url);
            CREATE TABLE IF NOT EXISTS usage (material TEXT, scene TEXT, profile TEXT, asset_id TEXT, created_utc TEXT);
            CREATE INDEX IF NOT EXISTS usage_material ON usage(material,scene);
            CREATE TABLE IF NOT EXISTS attributes (asset_id TEXT, field TEXT, value TEXT);
            CREATE INDEX IF NOT EXISTS attribute_lookup ON attributes(field,value,asset_id);''')
        for identifier,url,document in self.db.execute('SELECT id,url,document FROM assets').fetchall():
            if url and canonical_url(url)!=url:self.db.execute('UPDATE assets SET url=? WHERE id=?',(canonical_url(url),identifier))
            if not self.db.execute('SELECT 1 FROM attributes WHERE asset_id=? LIMIT 1',(identifier,)).fetchone():
                value=json.loads(document)
                for field in ['keywords','persons','places','events','period','tags','type','provider','license','orientation','width','height','duration','checksum']:
                    data=value.get(field);values=data if isinstance(data,list) else [data]
                    self.db.executemany('INSERT INTO attributes VALUES (?,?,?)',[(identifier,field,str(v).casefold()) for v in values if v is not None])
        self.db.commit()

    def close(self):self.db.close()
    def __enter__(self):return self
    def __exit__(self, *args):self.close()

    def records(self, query='', kind=None, **filters):
        ids=None
        for field,value in filters.items():
            if value is None:continue
            found={row[0] for row in self.db.execute('SELECT asset_id FROM attributes WHERE field=? AND value=?',(field,str(value).casefold()))}
            ids=found if ids is None else ids & found
        rows = [json.loads(row[0]) for row in self.db.execute('SELECT document FROM assets ORDER BY id')]
        if ids is not None:rows=[row for row in rows if row['asset_id'] in ids]
        tokens = re.findall(r'\w+', query.casefold())
        return [a for a in rows if (not kind or a['type'] == kind)
                and all(t in json.dumps(a, ensure_ascii=False).casefold() for t in tokens)
                and all((v in a.get(k,[]) if isinstance(a.get(k),list) else a.get(k)==v) for k,v in filters.items() if v is not None)]

    def get(self, identifier):
        row = self.db.execute('SELECT document FROM assets WHERE id=?', (identifier,)).fetchone()
        if not row:raise ValueError('Asset library ID inexistent: ' + identifier)
        value = json.loads(row[0]); self.check(value); return value

    def check(self, value):
        p = Path(value['local_path']).resolve()
        if not p.is_relative_to(self.root / 'objects') or not p.is_file() or core.sha(p) != value['checksum']:
            raise ValueError('Asset din bibliotecă lipsă/corupt; păstrat pentru audit.')
        return p

    def cached(self, checksum=None, url=None):
        if checksum:rows = self.db.execute('SELECT document FROM assets WHERE checksum=?', (checksum,))
        elif url:rows = self.db.execute('SELECT document FROM assets WHERE url=? ORDER BY rowid DESC', (canonical_url(url),))
        else:return None
        row = rows.fetchone()
        if not row:return None
        result = json.loads(row[0]); self.check(result); return result

    def publish(self, temporary, metadata, info=None):
        temporary = Path(temporary); info = info or inspect_media(temporary)
        checksum = core.sha(temporary)
        expected = metadata.get('checksum')
        if expected and expected != checksum:raise ValueError('Checksum asset diferit de cel declarat.')
        target = self.root / 'objects' / checksum[:2] / (checksum + '.' + info['extension'])
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if core.sha(target) != checksum:raise ValueError('Obiect existent corupt; nu este suprascris.')
        else:
            # Temporary is private, already validated; fsync precedes publication.
            with temporary.open('rb') as f:os.fsync(f.fileno())
            os.replace(temporary, target)
            fd = os.open(target.parent, os.O_DIRECTORY); os.fsync(fd); os.close(fd)
        value = dict(metadata); value.update(info)
        value['dimensions'] = [info['width'], info['height']]
        value.update(checksum=checksum, local_path=str(target), downloaded_at=metadata.get('downloaded_at') or core.now())
        value.setdefault('provider', 'local'); value.setdefault('license', 'LICENSE_UNKNOWN')
        for k in ['source_url', 'creator', 'license_url', 'attribution']:value.setdefault(k, '')
        value['asset_id'] = core.key([checksum, value['provider'], value['source_url'], value['creator'], value['license'], value['license_url']])[:24]
        for field in ['keywords', 'persons', 'places', 'events', 'period', 'tags']:value.setdefault(field, [])
        self.db.execute('INSERT OR REPLACE INTO assets VALUES (?,?,?,?)', (value['asset_id'], checksum, canonical_url(value['download_url']) if value.get('download_url') else None, json.dumps(value, ensure_ascii=False)))
        self.db.execute('DELETE FROM attributes WHERE asset_id=?',(value['asset_id'],))
        for field in ['keywords','persons','places','events','period','tags','type','provider','license','orientation','width','height','duration','checksum']:
            data=value.get(field);values=data if isinstance(data,list) else [data]
            self.db.executemany('INSERT INTO attributes VALUES (?,?,?)',[(value['asset_id'],field,str(v).casefold()) for v in values if v is not None])
        self.db.commit(); return value

    def ingest(self, path, metadata=None):
        source = Path(path).resolve(); metadata = dict(metadata or {})
        info = inspect_media(source); checksum = core.sha(source)
        if metadata.get('checksum') and metadata['checksum'] != checksum:
            raise ValueError('Checksum asset diferit de cel declarat la import.')
        metadata['checksum'] = checksum
        folder = self.root / 'attempts' / uuid.uuid4().hex; folder.mkdir(parents=True)
        temporary = folder / 'payload.part'
        with source.open('rb') as src, temporary.open('xb') as out:
            shutil.copyfileobj(src, out, 1024 * 1024); out.flush(); os.fsync(out.fileno())
        return self.publish(temporary, metadata, info)

    def download(self, candidate, opener=None):
        url = candidate['download_url']; asset_http.validate_url(url, resolve=False)
        cached = self.cached(candidate.get('checksum'), url)
        if cached and candidate.get('upstream_sha1'):
            with Path(cached['local_path']).open('rb') as source:digest=hashlib.file_digest(source,'sha1').hexdigest()
            expected=candidate['upstream_sha1'];matches=(digest==expected) if len(expected)==40 else (int(digest,16)==int(expected,36))
            if not matches:cached=None
        if cached:
            metadata = dict(cached); metadata.update(candidate); metadata['checksum'] = cached['checksum']
            metadata['downloaded_at'] = cached['downloaded_at']
            return self.publish(Path(cached['local_path']), metadata, {k:cached[k] for k in ['type','width','height','duration','extension','mime','orientation']})
        host=urlsplit(url).netloc
        cooldown=self.root/'cooldowns'/(core.key(host)+'.json')
        if cooldown.exists() and core.read(cooldown)['until_epoch']>time.time():
            raise ValueError('Provider cooldown activ; reîncearcă după Retry-After, fără ocolirea limitei.')
        opener = opener or asset_http.open_url
        folder = self.root / 'attempts' / uuid.uuid4().hex; folder.mkdir(parents=True)
        temporary = folder / 'payload.part'; receipt = folder / 'download.json'
        state = dict(url=url, created_utc=core.now(), phase='downloading', bytes=0)
        # Only the latest attempt for this URL can authorize a bounded resume.
        attempts=[]
        for old in (self.root/'attempts').glob('*/download.json'):
            try:
                saved=core.read(old)
                if saved.get('url')==url:attempts.append((old,saved))
            except (ValueError,OSError):continue
        offset=0;headers={};resume=None
        if attempts:
            old,saved=max(attempts,key=lambda item:item[1].get('created_utc',''))
            part=old.with_name('payload.part');etag=saved.get('etag','')
            if saved.get('resume_allowed') and etag and not etag.startswith('W/') and not any(c in etag for c in '\r\n') and part.exists() and 0<part.stat().st_size<saved.get('expected_bytes',0)<=MAX_BYTES and core.sha(part)==saved.get('partial_sha256'):
                shutil.copy2(part,temporary);offset=part.stat().st_size;resume=saved
                headers={'Range':f'bytes={offset}-','If-Range':etag};state['resumed_from']=str(old)
        core.write(receipt, state)
        try:
            response=opener(url,headers) if headers else opener(url)
            with response:
                status=getattr(response,'status',200)
                length=response.headers.get('Content-Length');response_length=int(length) if length else None
                if response_length is not None and not 0<response_length<=MAX_BYTES:raise ValueError('Content-Length excesiv/invalid.')
                expected=response_length
                if offset and status==206:
                    match=re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)',response.headers.get('Content-Range',''))
                    if not match or int(match[1])!=offset or int(match[3])!=resume['expected_bytes'] or int(match[2])!=int(match[3])-1 or response.headers.get('ETag')!=resume['etag']:
                        raise ValueError('Reluare Range ambiguă; fără publicare, următoarea încercare pornește de la zero.')
                    expected=int(match[3])
                    if response_length is not None and response_length!=expected-offset:raise ValueError('Content-Range/Length incompatibile.')
                elif status==200:offset=0
                else:raise ValueError('Răspuns HTTP neașteptat pentru download.')
                if expected is not None and expected>MAX_BYTES:raise ValueError('Download prea mare.')
                etag=response.headers.get('ETag','')
                state.update(etag=etag,expected_bytes=expected,content_type=response.headers.get('Content-Type'),
                             resume_allowed=bool(expected and etag and not etag.startswith('W/') and response.headers.get('Accept-Ranges')=='bytes'))
                core.write(receipt,state)
                count=offset
                with temporary.open('ab' if offset else 'wb') as out:
                    while True:
                        block=response.read(1024*1024)
                        if not block:break
                        count+=len(block)
                        if count>MAX_BYTES:raise ValueError('Download prea mare.')
                        out.write(block)
                    out.flush();os.fsync(out.fileno())
                if expected is not None and count!=expected:raise ValueError('Download incomplet: Content-Length diferit.')
                info=inspect_media(temporary,response.headers.get('Content-Type'))
            if candidate.get('upstream_sha1'):
                with temporary.open('rb') as source:digest=hashlib.file_digest(source,'sha1').hexdigest()
                expected_sha1=candidate['upstream_sha1']
                valid=(digest==expected_sha1) if len(expected_sha1)==40 else (int(digest,16)==int(expected_sha1,36))
                if not valid:raise ValueError('Checksum upstream SHA1 diferit.')
            result=self.publish(temporary,candidate,info)
            state.update(phase='complete',bytes=count,checksum=result['checksum'],asset_id=result['asset_id'],resume_allowed=False)
            core.write(receipt,state);return result
        except BaseException as error:
            if isinstance(error,HTTPError) and error.code==429:
                retry=error.headers.get('Retry-After','60') if error.headers else '60'
                try:until=time.time()+max(1,int(retry))
                except ValueError:
                    try:until=parsedate_to_datetime(retry).timestamp()
                    except (ValueError,TypeError):until=time.time()+60
                core.write(cooldown,dict(host=host,until_epoch=until,retry_after=retry,created_utc=core.now()))
            state.update(phase='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',error=str(error),
                         bytes=temporary.stat().st_size if temporary.exists() else 0,
                         partial_sha256=core.sha(temporary) if temporary.exists() else None)
            core.write(receipt,state);raise

    def use(self, material, scene, profile, asset):
        self.db.execute('INSERT INTO usage VALUES (?,?,?,?,?)', (material, scene, profile or 'default', asset['asset_id'], core.now())); self.db.commit()

    def usage_counts(self):
        return dict(self.db.execute('SELECT asset_id, COUNT(*) FROM usage GROUP BY asset_id'))
