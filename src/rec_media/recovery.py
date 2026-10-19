"""Recoverable preparation of analysis PCM; incomplete attempts remain diagnostic."""
import os
from pathlib import Path
import uuid

from .core import assemble, checked, ff, key, now, probe, read, sha, write


def prepare_analysis(document, material, work):
    work=Path(work);work.mkdir(parents=True,exist_ok=True)
    for clip in material['timeline']:checked(document,clip['source'])
    signature=key(dict(timeline=material['timeline'],rate=material['sample_rate'],frames=material['frames'],analysis_rate=16000,format='pcm_f32le',adapter=1))
    pcm=work/'analysis.wav'; receipt=work/'analysis-receipt.json'
    def validate(path):
        stream=probe(path)['streams'][0]
        if stream['codec_name']!='pcm_f32le' or int(stream['sample_rate'])!=16000 or stream['channels']!=1:raise ValueError('WAV analiză invalid.')
        expected=material['frames']*16000/material['sample_rate']
        if abs(int(stream['duration_ts'])-expected)>1:raise ValueError('WAV analiză incomplet.')
        ff(['-xerror','-i',path,'-f','null','-'])
    try:
        old=read(receipt)
        if old['request']==signature and old['sha256']==sha(pcm):
            validate(pcm)
            return pcm,dict(reused=True,receipt=str(receipt),sha256=old['sha256'])
    except (OSError,ValueError,KeyError,TypeError):pass
    attempt=work/'preparation'/uuid.uuid4().hex;attempt.mkdir(parents=True)
    write(attempt/'state.json',dict(phase='assembling',created_utc=now(),request=signature))
    try:
        master=assemble(document,material,attempt/'master.wav')
        temporary=attempt/'analysis.wav'
        ff(['-i',master,'-ac','1','-ar','16000','-c:a','pcm_f32le',temporary])
        validate(temporary); digest=sha(temporary)
        # Preserve any older/corrupt legacy result for diagnosis, never trust existence alone.
        if pcm.exists():os.replace(pcm,attempt/'previous-analysis.wav')
        os.replace(temporary,pcm)
        result=dict(request=signature,sha256=digest,created_utc=now(),attempt=str(attempt))
        write(receipt,result);write(attempt/'state.json',dict(result,phase='complete'))
        return pcm,dict(reused=False,receipt=str(receipt),sha256=digest)
    except BaseException as error:
        write(attempt/'state.json',dict(phase='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',error=str(error),created_utc=now(),request=signature))
        raise
