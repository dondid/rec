"""Optional local image job contract. No model downloading or implicit execution."""
from pathlib import Path

from .core import now, read, sha, write


def image_plan(request,output):
    request=Path(request).resolve();output=Path(output).resolve()
    if output.exists():raise ValueError('Plan backend existent.')
    job=read(request)
    if job.get('backend')!='stable-diffusion.cpp':raise ValueError('Backend pregătit: stable-diffusion.cpp.')
    if not isinstance(job.get('prompt'),str) or not job['prompt'].strip():raise ValueError('Prompt gol.')
    for field in ('width','height'):
        if type(job.get(field)) is not int or not 256<=job[field]<=2048 or job[field]%64:raise ValueError('Dimensiuni imagini: multipli de 64, 256–2048.')
    if type(job.get('seed')) is not int:raise ValueError('Seed întreg explicit necesar.')
    blockers=[];identity={}
    for field in ('executable','model'):
        ref=job.get(field)
        if not isinstance(ref,dict):blockers.append(field+' absent');continue
        path=Path(ref['path']);path=path if path.is_absolute() else request.parent/path
        if not path.is_file():blockers.append(field+' neinstalat');continue
        if sha(path)!=ref.get('sha256'):raise ValueError(field+' cu hash diferit de request.')
        if not ref.get('revision') or not ref.get('license'):raise ValueError(field+' cere revizie și licență explicită.')
        identity[field]=dict(ref,path=str(path.resolve()),bytes=path.stat().st_size)
    # This command is intentionally a portable job specification, not an untested runner.
    result=dict(schema_version=1,backend=job['backend'],created_utc=now(),job=job,identity=identity,
                technical_status='blocked' if blockers else 'planned',blockers=blockers,
                execution_status='not_executed',approval_status='pending',
                next_step='Run and validate the pinned sd-cli on suitable hardware; import the image with media scenes/thumbnail. No cloud fallback.')
    write(output,result);return result
