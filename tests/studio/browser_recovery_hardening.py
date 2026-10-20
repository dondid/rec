"""Browser cancel/resume plus active-server restart in an isolated project."""
import argparse
from pathlib import Path
from recovery_acceptance import run
p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--offline-namespace',action='store_true');a=p.parse_args()
if 'work/studio/hardening-' not in str(a.project.resolve()):raise RuntimeError('Isolated hardening project required.')
run(a.project,a.report,a.offline_namespace,browser_review=True)
