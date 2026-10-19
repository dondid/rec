"""Manual assets on observed audio intervals; no visual AI inference."""
from pathlib import Path
import re

from .core import load, read, write
from .derive import split_plan


def propose(value,output,folder=None,images=None,intervals=None):
    document,m=load(value); output=Path(output).resolve()
    if output.exists():raise ValueError('Plan existent.')
    if folder:
        assets=sorted(p.resolve() for p in Path(folder).iterdir() if p.suffix.lower() in ('.png','.jpg','.jpeg','.webp','.mp4','.mkv','.mov'))
    else:assets=[Path(p).resolve() for p in images or []]
    if not assets or any(not p.is_file() for p in assets):raise ValueError('Assets lipsă sau listă goală.')
    _,_,plan=split_plan(value,intervals=read(intervals) if intervals else None,parts=len(assets))
    if len(plan['intervals'])!=len(assets):raise ValueError('Numărul intervalelor sigure diferă de numărul assets; furnizează intervale explicite.')
    if not m['alignment']:raise ValueError('Planul automat de scene cere alinierea existentă a textului cunoscut.')
    tokens=list(re.finditer(r'\S+',m['text_spoken']));words=m['alignment']['words'];cursor=0;spans=[]
    for word in words:
        count=len(word['spoken'].split());spans.append((tokens[cursor].start(),tokens[cursor+count-1].end()));cursor+=count
    result=[]
    for i,((a,b),asset) in enumerate(zip(plan['intervals'],assets),1):
        covered=[j for j,w in enumerate(words) if a<=w['start'] and w['end']<=b]
        if not covered:raise ValueError('Scenă fără pasaj aliniat; ajustează intervalele.')
        left=spans[covered[0]][0];right=spans[covered[-1]][1]
        result.append(dict(id=f'scene-{i:03d}',start=a,end=b,text_range=[left,right],anchor=m['text_spoken'][left:right],
            path=str(asset),kind='video' if asset.suffix.lower() in ('.mp4','.mkv','.mov') else 'image',
            description='Asset furnizat manual; relevanța trebuie aprobată.',motion='none',transition='cut',focal=[.5,.5],approval_status='pending',license='unknown',provenance='local user supplied'))
    data=dict(schema_version=1,scenes=result,status='proposal_requires_review',asset_order='lexicographic' if folder else 'explicit')
    write(output,data);return data
