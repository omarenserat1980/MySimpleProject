#!/usr/bin/env python3
from __future__ import annotations
import json, os, pathlib, subprocess, sys, time
ROOT = pathlib.Path(__file__).resolve().parents[2]
REPORT = ROOT / 'brain_v12' / 'ci-reports'
REPORT.mkdir(parents=True, exist_ok=True)
def run(cmd):
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    return {'command': cmd, 'returncode': p.returncode, 'stdout': p.stdout[-12000:], 'stderr': p.stderr[-12000:]}
checks = [run([sys.executable, '-m', 'compileall', '-q', 'brain_v12'])]
for tool in ('ffmpeg', 'ffprobe'):
    checks.append(run(['bash', '-lc', f'command -v {tool} >/dev/null 2>&1']))
result = {'schema':'brain-ci-repair/v1','timestamp':int(time.time()),'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),'checks':checks,'passed':all(x['returncode']==0 for x in checks)}
(REPORT / 'repair-report.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
sys.exit(0 if result['passed'] else 1)
