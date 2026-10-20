import argparse
import contextlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import uuid

from .core import ROOT,VERSION,config,ff,key,load,lock,now,probe,read,reference,resolve,sha,tool,write


def parser():
    p=argparse.ArgumentParser(description='REC media local CPU; fără descărcări la procesare.')
    p.add_argument('--config',type=Path,default=ROOT/'media.json')
    p.add_argument('--report',type=Path)
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor')
    g=sub.add_parser('gui',help='REC Production Studio local, fără cloud.')
    g.add_argument('--host',default='127.0.0.1');g.add_argument('--port',type=int,default=8765)
    g.add_argument('--no-browser',action='store_true')
    s=sub.add_parser('audio-mix');s.add_argument('material');s.add_argument('--output-dir',type=Path);s.add_argument('--output',type=Path)
    s.add_argument('--mux-video',type=Path,help='Copiază streamul video existent; schimbă numai audio')
    actions=s.add_mutually_exclusive_group(required=True)
    actions.add_argument('--inspect',action='store_true');actions.add_argument('--validate',type=Path)
    actions.add_argument('--set',type=Path);actions.add_argument('--disable',action='store_true')
    actions.add_argument('--render',action='store_true');actions.add_argument('--verify',type=Path)
    s=sub.add_parser('image-plan');s.add_argument('request',type=Path);s.add_argument('--output',required=True,type=Path)
    s=sub.add_parser('workflow');s.add_argument('plan',type=Path);s.add_argument('--only',nargs='+');s.add_argument('--disable',nargs='+');s.add_argument('--rerun',nargs='+')
    s=sub.add_parser('synthesize-parts');s.add_argument('manifest',type=Path);s.add_argument('--output-dir',required=True,type=Path);s.add_argument('--apply',action='store_true')
    s=sub.add_parser('split-text');s.add_argument('text',type=Path);s.add_argument('--output-dir',required=True,type=Path)
    method=s.add_mutually_exclusive_group(required=True)
    method.add_argument('--parts',type=int);method.add_argument('--target-duration',type=float);method.add_argument('--chapters',action='store_true');method.add_argument('--delimiter');method.add_argument('--manual-ranges',type=Path);method.add_argument('--semantic',action='store_true')
    s.add_argument('--words-per-minute',type=float,default=150)
    s=sub.add_parser('merge-text');s.add_argument('manifest',type=Path);s.add_argument('--output',required=True,type=Path)
    s=sub.add_parser('init');s.add_argument('--id',required=True);s.add_argument('--audio',required=True,type=Path);s.add_argument('--text',type=Path);s.add_argument('--image',type=Path);s.add_argument('--tts-report',type=Path);s.add_argument('--sample-rate',type=int)
    s=sub.add_parser('convert-narration');s.add_argument('material');s.add_argument('--id',required=True);s.add_argument('--sample-rate',type=int,default=22050)
    s=sub.add_parser('compile');s.add_argument('--id',required=True);s.add_argument('--materials',required=True,nargs='+');s.add_argument('--composition',required=True,type=Path);s.add_argument('--plan-only',action='store_true')
    s=sub.add_parser('compile-video');s.add_argument('material');s.add_argument('--videos',required=True,type=Path);s.add_argument('--output',required=True,type=Path);s.add_argument('--profiles',default='portrait')
    s=sub.add_parser('align');s.add_argument('material')
    backend=s.add_mutually_exclusive_group(required=True)
    backend.add_argument('--words',type=Path);backend.add_argument('--backend',choices=['ctc-ro'])
    s.add_argument('--provenance');s.add_argument('--model',type=Path);s.add_argument('--windows',type=Path);s.add_argument('--max-windows',type=int);s.add_argument('--segments',help='Indici CTC de la zero, separați prin virgulă')
    s=sub.add_parser('alignment-review');s.add_argument('material');s.add_argument('--output',type=Path);s.add_argument('--apply',type=Path);s.add_argument('--validate',type=Path);s.add_argument('--media',type=Path)
    s=sub.add_parser('scene-plan');s.add_argument('material');s.add_argument('--output',required=True,type=Path);assets=s.add_mutually_exclusive_group(required=True);assets.add_argument('--folder',type=Path);assets.add_argument('--images',type=Path,nargs='+');s.add_argument('--intervals',type=Path)
    s=sub.add_parser('scenes');s.add_argument('material');s.add_argument('--scene');s.add_argument('--profile',choices=['landscape','portrait','custom','square']);s.add_argument('--library-root',type=Path)
    action=s.add_mutually_exclusive_group()
    action.add_argument('--plan',type=Path);action.add_argument('--inspect',action='store_true');action.add_argument('--alternatives',action='store_true')
    action.add_argument('--select');action.add_argument('--replace',type=Path);action.add_argument('--remove',action='store_true');action.add_argument('--restore',action='store_true');action.add_argument('--set',type=Path);action.add_argument('--auto',action='store_true');action.add_argument('--sequence',type=Path)
    s.add_argument('--approve',action='store_true');s.add_argument('--allow-unknown-license',action='store_true')
    s=sub.add_parser('assets');s.add_argument('--library-root',type=Path)
    actions=s.add_subparsers(dest='asset_command',required=True)
    a=actions.add_parser('search');a.add_argument('material');a.add_argument('--scene',required=True);a.add_argument('--provider',nargs='+',choices=['commons','openverse','pexels'],default=['commons','openverse']);a.add_argument('--query');a.add_argument('--type',choices=['image','video'],default='image');a.add_argument('--limit',type=int,default=8);a.add_argument('--mode',choices=['manual','assisted','auto'],default='assisted')
    a=actions.add_parser('queries');a.add_argument('material');a.add_argument('--scene',required=True)
    a=actions.add_parser('list');a.add_argument('--query',default='');a.add_argument('--type',choices=['image','video']);a.add_argument('--filters',type=Path)
    a=actions.add_parser('import');a.add_argument('path',type=Path);a.add_argument('--metadata',type=Path)
    a=actions.add_parser('download');a.add_argument('material');a.add_argument('--scene',required=True);d=a.add_mutually_exclusive_group(required=True);d.add_argument('--candidate');d.add_argument('--all',action='store_true');a.add_argument('--rendition',choices=['original','thumbnail'],default='original')
    a=actions.add_parser('review');a.add_argument('material');a.add_argument('--output-dir',required=True,type=Path)
    a=actions.add_parser('credits');a.add_argument('material');a.add_argument('--output-dir',type=Path);a.add_argument('--profiles',help='Profile efectiv publicate, separate prin virgulă')
    s=sub.add_parser('titles');s.add_argument('material');s.add_argument('--manual');s.add_argument('--select');s.add_argument('--approve',action='store_true');s.add_argument('--unlock',action='store_true');s.add_argument('--candidates',type=int)
    for name in ['subtitles','thumbnail','render']:
        s=sub.add_parser(name);s.add_argument('material');s.add_argument('--profiles',default='landscape');s.add_argument('--width',type=int);s.add_argument('--height',type=int)
        if name=='subtitles':
            s.add_argument('--mode',choices=['classic','highlight','scroll'],default='classic');s.add_argument('--output-dir',required=True,type=Path)
            s.add_argument('--ass-preset',choices=['safe','boxed','minimal'])
        elif name=='thumbnail':
            s.add_argument('--text');s.add_argument('--image',type=Path);s.add_argument('--scene');s.add_argument('--variant',choices=['panel','top'],default='panel');s.add_argument('--format',choices=['png','jpeg'],default='png');s.add_argument('--output-dir',required=True,type=Path)
        else:
            s.add_argument('--image',type=Path);s.add_argument('--subtitles',choices=['off','classic','highlight','scroll'],default='off');s.add_argument('--title');s.add_argument('--force',action='store_true');s.add_argument('--plan-only',action='store_true')
            s.add_argument('--ass-preset',choices=['safe','boxed','minimal'])
            s.add_argument('--rerender-changed',action='store_true',help='Cu --resume-run: păstrează intermediarii anteriori și recalculează numai scenele schimbate')
            s.add_argument('--resume-run',help='Reia un run cu scene verificate prin receipts/hash, fără rerandare')
            s.add_argument('--output-root',type=Path,help='Rădăcină alternativă; exportă în <root>/<material>/<profil>/video.mp4')
    s=sub.add_parser('split');s.add_argument('material');s.add_argument('--mode',choices=['partition','extract'],default='partition');s.add_argument('--intervals',type=Path);s.add_argument('--parts',type=int);s.add_argument('--target-seconds',type=float);s.add_argument('--max-seconds',type=float,help='Plafon strict în eșantioane; conflict explicit dacă limitele nu îl respectă');s.add_argument('--prefix',required=True);s.add_argument('--apply',action='store_true')
    s=sub.add_parser('merge');s.add_argument('--id',required=True);s.add_argument('--materials',required=True,nargs='+');s.add_argument('--plan-only',action='store_true');s.add_argument('--composition',type=Path)
    s=sub.add_parser('batch');s.add_argument('file',type=Path)
    s=sub.add_parser('verify');s.add_argument('video',type=Path)
    return p


def execute(a):
    # Compatibility for existing Python callers that override cli.ROOT.
    from . import services
    services.ROOT = ROOT
    return services.execute(a)


def main(argv=None):
    a=parser().parse_args(argv)
    try:
        if a.command == 'gui':
            from .studio.server import serve
            return serve(a.host,a.port,a.no_browser)
        from . import services
        services.ROOT = ROOT
        result=services.run(a)
        print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
        return 1 if isinstance(result,dict) and result.get('technical_status') in ('failed','blocked') else 0
    except KeyboardInterrupt:
        print('Întrerupt; exporturile valide sunt păstrate. Repetă comanda.',file=sys.stderr);return 130
    except Exception as e:
        print(f'Eroare media: {e}',file=sys.stderr);return 1
