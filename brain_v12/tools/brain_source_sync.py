#!/usr/bin/env python3
"""Safe source sync helper for the live Brain checkout."""
from __future__ import annotations
import os, subprocess, sys
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

def run(*args):
    return subprocess.run(args,cwd=ROOT,text=True,capture_output=True,timeout=60)

def main():
    status=run('git','status','--porcelain')
    if status.returncode:
        print('SOURCE_SYNC_GIT_UNAVAILABLE',status.stderr.strip()); return 2
    if status.stdout.strip():
        print('SOURCE_SYNC_SKIPPED_LOCAL_CHANGES')
        print(status.stdout.strip())
        return 3
    pull=run('git','pull','--ff-only')
    print(pull.stdout.strip())
    if pull.returncode:
        print('SOURCE_SYNC_FAILED',pull.stderr.strip()); return pull.returncode
    required=('brain_v12/brain/service_catalog.py','brain_v12/brain/security_guard.py','brain_v12/brain/test_security_guard.py','brain_v12/self_healing/future_evolution_executor.py','brain_v12/self_healing/test_future_evolution_executor.py')
    missing=[p for p in required if not os.path.isfile(os.path.join(ROOT,p))]
    if missing:
        print('SOURCE_SYNC_MISSING',*missing,sep='\n'); return 4
    print('SOURCE_SYNC_VERIFIED')
    for p in required: print('PRESENT',p)
    return 0
if __name__=='__main__': sys.exit(main())
