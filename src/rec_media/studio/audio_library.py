"""Additive audio table in the existing content-addressed asset library."""
from pathlib import Path
import json
import os
import shutil
import sqlite3
import uuid
from .. import core, audio_mix
from . import security

TAGS={'music','sfx','ambience'}


def validate(values):
    if not isinstance(values,dict) or set(values)-{'path','tags','creator','license','source','attribution','checksum'}:raise ValueError('Metadate audio necunoscute.')
    security.media_file(values['path']);tags=values.get('tags',[])
    if not isinstance(tags,list) or not tags or len(set(tags))!=len(tags) or any(t not in TAGS for t in tags):raise ValueError('Alege tags explicite: music, sfx, ambience.')
    for name in ('creator','license','source','attribution'):
        if name in values and (not isinstance(values[name],str) or len(values[name])>4000):raise ValueError(f'{name}: text de maximum 4000 caractere.')
    if 'checksum' in values and (not isinstance(values['checksum'],str) or len(values['checksum'])!=64):raise ValueError('Checksum audio invalid.')
    return values


def records(query='',tag=None):
    if tag is not None and tag not in TAGS:raise ValueError('Tag audio invalid.')
    db=core.ROOT/'assets/library/library.sqlite3'
    if not db.is_file():return []
    with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as c:
        if not c.execute("SELECT 1 FROM sqlite_master WHERE name='studio_audio'").fetchone():return []
        result=[json.loads(r[0]) for r in c.execute('SELECT document FROM studio_audio ORDER BY id')]
    tokens=query.casefold().split()
    return [a for a in result if (not tag or tag in a['tags']) and all(t in json.dumps(a,ensure_ascii=False).casefold() for t in tokens)]


def import_audio(values):
    validate(values);source=security.media_file(values['path']);library=core.ROOT/'assets/library'
    attempt=library/'audio-imports'/uuid.uuid4().hex;attempt.mkdir(parents=True)
    state=dict(phase='running',utc=core.now());core.write(attempt/'state.json',state)
    try:
        before=core.sha(source)
        if values.get('checksum',before)!=before:raise ValueError('Checksum declarat diferit; import refuzat înainte de publicare.')
        info=audio_mix.source_info(source)
        frames=sum(len(a) for a in audio_mix.pcm(source,info['sample_rate']))
        if frames<=0:raise ValueError('Audio fără eșantioane decodate.')
        if core.sha(source)!=before:raise ValueError('Audio schimbat în timpul validării.')
        with source.open('rb') as f:head=f.read(32)
        if head.startswith((b'RIFF',b'RF64')):extension,mime='wav','audio/wav'
        elif head.startswith(b'fLaC'):extension,mime='flac','audio/flac'
        elif head.startswith(b'OggS'):extension,mime='ogg','audio/ogg'
        elif head[4:8]==b'ftyp':extension,mime='m4a','audio/mp4'
        elif head.startswith(b'ID3') or (head and head[0]==255):extension,mime='mp3','audio/mpeg'
        else:raise ValueError('MIME audio real nepermis; nu importa video ca audio implicit.')
        blob=library/'objects'/before[:2]/(before+'.'+extension);blob.parent.mkdir(parents=True,exist_ok=True)
        temporary=attempt/('blob.part.'+extension);shutil.copyfile(source,temporary)
        with temporary.open('rb') as f:os.fsync(f.fileno())
        if core.sha(temporary)!=before:raise ValueError('Copie audio coruptă; fișierul incomplet este păstrat.')
        with core.lock():
            if blob.exists():
                if not blob.is_file() or core.sha(blob)!=before:raise ValueError('Blob existent incompatibil; păstrat pentru audit.')
            else:
                os.replace(temporary,blob)
                fd=os.open(blob.parent,os.O_RDONLY)
                try:os.fsync(fd)
                finally:os.close(fd)
            record=dict(asset_id='audio-'+before[:24],type='audio',checksum=before,local_path=str(blob),mime=mime,
                frames=frames,duration=frames/info['sample_rate'],sample_rate=info['sample_rate'],channels=info['channels'],codec=info['codec'],size=blob.stat().st_size,
                tags=values['tags'],creator=values.get('creator',''),license=values.get('license','unknown') or 'unknown',source=values.get('source',''),attribution=values.get('attribution',''),
                imported_utc=core.now(),technical_status='passed',listening_review='not_listened',editorial_review='not_reviewed')
            with sqlite3.connect(library/'library.sqlite3') as c:
                c.execute('CREATE TABLE IF NOT EXISTS studio_audio (id TEXT PRIMARY KEY, checksum TEXT NOT NULL UNIQUE, document TEXT NOT NULL)')
                previous=c.execute('SELECT document FROM studio_audio WHERE id=?',(record['asset_id'],)).fetchone()
                if previous:core.write(attempt/'before.json',json.loads(previous[0]))
                core.write(attempt/'after.json',record)
                c.execute('INSERT OR REPLACE INTO studio_audio VALUES (?,?,?)',(record['asset_id'],before,json.dumps(record,ensure_ascii=False,allow_nan=False)))
            state.update(phase='complete',finished_utc=core.now(),asset_id=record['asset_id']);core.write(attempt/'state.json',state)
        return dict(technical_status='passed',asset=record,audit=str(attempt),note='Validare tehnică; licența/provenance sunt furnizate explicit, fără aprobare auditivă/editorială.')
    except BaseException as e:
        state.update(phase='interrupted' if isinstance(e,KeyboardInterrupt) else 'failed',error=str(e),finished_utc=core.now());core.write(attempt/'state.json',state);raise
