"""Loopback HTTP server with origin checks, CSRF tokens and scoped file serving."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
import base64
import fcntl
import json
import mimetypes
import os
import secrets
import socket
import shutil
import subprocess
import threading
import webbrowser
from .. import core
from . import VERSION, catalog, data, operations, security
from .jobs import Queue
from . import audio_library, platform_support

STATIC=Path(__file__).parent/'static'


class Server(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address):
        super().__init__(address,Handler)
        self.csrf=secrets.token_urlsafe(32);self.queue=Queue()
        self.allowed_hosts={f'{address[0]}:{self.server_port}',f'127.0.0.1:{self.server_port}',f'localhost:{self.server_port}'}


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass  # Never log paths/query payloads or secrets.

    def headers_ok(self,write=False):
        host=self.headers.get('Host','')
        if host not in self.server.allowed_hosts:raise ValueError('Host refuzat.')
        origin=self.headers.get('Origin')
        if origin and origin not in {'http://'+h for h in self.server.allowed_hosts}:raise ValueError('Origin refuzat.')
        if self.headers.get('Sec-Fetch-Site')=='cross-site':raise ValueError('Cross-site refuzat.')
        if write and not secrets.compare_digest(self.headers.get('X-REC-CSRF',''),self.server.csrf):raise ValueError('Token CSRF invalid.')

    def send(self,payload,status=200,kind='application/json; charset=utf-8'):
        if not isinstance(payload,bytes):payload=json.dumps(security.public(payload),ensure_ascii=False,allow_nan=False).encode()
        self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(payload)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self' blob:; connect-src 'self'; frame-src 'self'; frame-ancestors 'self'; base-uri 'none'; form-action 'self'")
        self.end_headers();self.wfile.write(payload)

    def params(self):return {k:v[0] for k,v in parse_qs(urlsplit(self.path).query).items()}

    def do_GET(self):
        try:
            self.headers_ok();route=urlsplit(self.path).path;q=self.params()
            if route=='/':return self.send((STATIC/'index.html').read_bytes(),kind='text/html; charset=utf-8')
            if route in ('/app.js','/hardening.js','/style.css'):
                p=STATIC/route[1:];return self.send(p.read_bytes(),kind='text/javascript' if p.suffix=='.js' else 'text/css')
            if route=='/api/bootstrap':return self.send(dict(version=VERSION,csrf=self.server.csrf,project=str(core.ROOT),materials=data.materials(),jobs=self.server.queue.listing(),catalog=catalog.catalog('media')+catalog.catalog('tts')))
            if route=='/api/material':return self.send(data.detail(q['id']))
            if route=='/api/ctc':
                p,m=security.material(q['id'])
                from ..review import bindings
                return self.send(dict(**bindings(p,m),sample_rate=m['sample_rate'],frames=m['frames'],words=m['alignment']['words'],normalizations=m['alignment'].get('normalization',[])))
            if route=='/api/text':return self.send(operations.text_state(q['id']))
            if route=='/api/jobs':return self.send(self.server.queue.listing())
            if route=='/api/job':return self.send(self.server.queue.detail(q['id']))
            if route=='/api/outputs':return self.send(data.outputs(q.get('material')))
            if route=='/api/scene-source':
                from .previews import source_metadata
                from .. import asset_scenes
                p,m=security.material(q['id']);profile=q.get('profile','landscape')
                if profile not in ('landscape','portrait'):raise ValueError('Profil invalid.')
                scene=asset_scenes.effective(asset_scenes.find(m,q['scene']),profile)
                return self.send(source_metadata(p,scene,m['sample_rate']))
            if route=='/api/audio-library':
                return self.send([data.decorate_asset(a,core.ROOT/'media.json') for a in audio_library.records(q.get('query',''),q.get('tag') or None)])
            if route=='/api/paths':return self.send(platform_support.paths(q.get('path','output')))
            if route=='/api/library':
                rows=operations.library_records();query=q.get('query','').casefold()
                return self.send([data.decorate_asset(a,core.ROOT/'media.json') for a in rows if query in json.dumps(a,ensure_ascii=False).casefold()])
            if route=='/api/settings':return self.send(dict(media=core.read(core.ROOT/'media.json'),tts=core.read(core.ROOT/'rec.json'),hardware=data.hardware(),defaults=core.read(core.ROOT/'work/studio/defaults.json') if (core.ROOT/'work/studio/defaults.json').exists() else {}))
            if route=='/api/files':
                p=security.path(q.get('path','input'),exists=True,directory=True)
                rows=[]
                for f in sorted(p.iterdir(),key=lambda x:(not x.is_dir(),x.name)):
                    try:
                        security.path(f)
                        if f.is_dir() or f.suffix.lower() in security.EXTENSIONS:rows.append(dict(name=f.name,path=str(f.relative_to(core.ROOT)),directory=f.is_dir(),size=None if f.is_dir() else f.stat().st_size))
                    except ValueError:continue
                return self.send(rows[:500])
            if route=='/api/hash':
                p=security.path(q['path'],exists=True)
                if p.suffix not in security.EXTENSIONS:raise ValueError('Tip nepermis.')
                return self.send(dict(path=q['path'],sha256=core.sha(p),size=p.stat().st_size))
            if route=='/files':return self.file(q['path'])
            self.send(dict(error='Rută inexistentă.'),404)
        except (BrokenPipeError,ConnectionResetError):pass
        except (ValueError,KeyError,OSError,TypeError) as e:self.send(dict(error=str(e)),400)
        except Exception as e:self.send(dict(error='Operația locală a eșuat: '+str(e)),500)

    def file(self,value):
        p=security.path(value,exists=True)
        if not p.is_file() or p.suffix.lower() not in security.EXTENSIONS or '.part' in p.name:raise ValueError('Fișier nepublicabil.')
        mime=mimetypes.guess_type(p.name)[0] or 'application/octet-stream'
        start=0;end=p.stat().st_size-1;status=200
        rng=self.headers.get('Range')
        if rng:
            import re
            m=re.fullmatch(r'bytes=(\d+)-(\d*)',rng)
            if not m:raise ValueError('Range invalid.')
            start=int(m[1]);end=min(end,int(m[2])) if m[2] else end
            if not 0<=start<=end<p.stat().st_size:self.send(dict(error='Range invalid'),416);return
            status=206
        self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(end-start+1));self.send_header('Accept-Ranges','bytes')
        self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cache-Control','no-store')
        self.send_header('Content-Security-Policy',"sandbox; default-src 'none'; style-src 'unsafe-inline'")
        if p.suffix in ('.html','.json','.md','.txt','.log','.ass','.srt'):self.send_header('Content-Disposition','attachment')
        if status==206:self.send_header('Content-Range',f'bytes {start}-{end}/{p.stat().st_size}')
        self.end_headers()
        with p.open('rb') as f:
            f.seek(start);remaining=end-start+1
            while remaining:
                block=f.read(min(1024*256,remaining))
                if not block:break
                self.wfile.write(block);remaining-=len(block)

    def do_POST(self):
        try:
            self.headers_ok(write=True)
            if self.headers.get('Content-Type','').partition(';')[0]!='application/json':raise ValueError('Content-Type JSON obligatoriu.')
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=12_000_000:raise ValueError('Cerere goală/prea mare.')
            body=json.loads(self.rfile.read(length));route=urlsplit(self.path).path
            if route=='/api/jobs':return self.send(self.server.queue.submit(body),202)
            if route=='/api/cancel':return self.send(self.server.queue.cancel(body['id']))
            if route=='/api/resume':return self.send(self.server.queue.resume(body['id']),202)
            if route=='/api/render-plan':return self.send(operations.render_plan(body))
            if route=='/api/audio-undo':return self.send(operations.undo_audio(body['material']))
            if route=='/api/invalidation':return self.send(operations.invalidation(body['material'],body['scene'],body.get('profile'),body.get('settings'),body.get('candidate')))
            if route=='/api/text':return self.send(operations.save_text(body['material'],body['text'],body['expected']))
            if route=='/api/subtitle-style':return self.send(operations.save_subtitles(body['material'],body.get('style',{}),body.get('expected'),body.get('undo',False)))
            if route=='/api/duplicate':return self.send(operations.duplicate(body['material'],body['id']))
            if route=='/api/upload':return self.upload(body)
            if route=='/api/defaults':
                if set(body)-{'profile','subtitle_preset','theme'} or body.get('profile','landscape') not in ('landscape','portrait','square') or body.get('subtitle_preset','safe') not in ('safe','boxed','minimal') or body.get('theme','dark') not in ('dark','light'):raise ValueError('Preferințe invalide.')
                core.write(core.ROOT/'work/studio/defaults.json',body);return self.send(dict(saved=True))
            if route=='/api/open-folder':
                return self.send(platform_support.open_folder(body['path']))
            self.send(dict(error='Rută inexistentă.'),404)
        except (BrokenPipeError,ConnectionResetError):pass
        except (ValueError,KeyError,OSError,TypeError) as e:self.send(dict(error=str(e)),400)
        except Exception as e:self.send(dict(error='Operația locală a eșuat: '+str(e)),500)

    def upload(self,body):
        import uuid
        name=Path(body.get('name','')).name;suffix=Path(name).suffix.lower()
        if suffix not in {'.txt','.json','.png','.jpg','.jpeg','.webp','.gif','.mp4','.webm','.mkv','.wav','.mp3','.flac','.ogg','.m4a'}:raise ValueError('Tip upload nepermis.')
        raw=base64.b64decode(body['data'],validate=True)
        if not 0<len(raw)<=8_000_000:raise ValueError('Upload limitat la 8 MB; folosește picker pentru fișierele mari.')
        folder=core.ROOT/'work/studio/imports'/uuid.uuid4().hex;folder.mkdir(parents=True);temp=folder/('incoming.part'+suffix);temp.write_bytes(raw)
        try:
            if suffix=='.txt':raw.decode('utf-8-sig')
            elif suffix=='.json':security.validate_references(json.loads(raw),folder/name)
            elif suffix in ('.wav','.mp3','.flac','.ogg','.m4a'):
                from ..audio_mix import source_info
                source_info(temp)
                core.ff(['-xerror','-protocol_whitelist','file,pipe','-i',temp,'-map','0:a:0','-f','null','-'])
            else:
                from ..asset_library import inspect_media
                inspect_media(temp)
        except Exception:
            # Preserve rejected bytes for audit; never publish an invalid upload.
            raise ValueError('Upload invalid; fișierul incomplet rămâne în staging pentru audit.')
        target=folder/name;os.replace(temp,target)
        return self.send(dict(path=str(target.relative_to(core.ROOT)),sha256=core.sha(target),published=True))


def serve(host='127.0.0.1',port=8765,no_browser=False):
    if not 0<=port<=65535:raise ValueError('Port invalid.')
    # Explicit --host is supported; bind stays loopback by default.
    folder=core.ROOT/'work/studio';folder.mkdir(parents=True,exist_ok=True)
    with (folder/'server.lock').open('a') as guard:
        try:fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('Un Studio este deja pornit în acest proiect.')
        try:server=Server((host,port))
        except OSError as e:raise ValueError(f'Port indisponibil {host}:{port}: {e}') from e
        url=f'http://{host}:{server.server_port}'
        print(f'REC Studio {VERSION}: {url}',flush=True)
        if not no_browser:threading.Timer(.4,lambda:webbrowser.open(url)).start()
        try:server.serve_forever(poll_interval=.3)
        except KeyboardInterrupt:print('Studio oprit. Joburile și checkpointurile sunt păstrate.',flush=True)
        finally:server.queue.stop.set();server.server_close()
    return 0
