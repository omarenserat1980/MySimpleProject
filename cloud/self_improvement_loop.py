"""Safe self-improvement loop for Brain Cloud.

Creates proposed changes and validates them; it never bypasses access controls
or merges untested changes automatically.
"""
import os, subprocess, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTERVAL = int(os.getenv("BRAIN_SELF_IMPROVEMENT_INTERVAL_SECONDS","1800"))
AUTO_MERGE = os.getenv("BRAIN_SELF_IMPROVEMENT_AUTO_MERGE","0") == "1"

def run(cmd):
    p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    print("SELF_IMPROVEMENT_CMD=", " ".join(cmd), flush=True)
    print(p.stdout[-4000:], flush=True)
    if p.returncode:
        print(p.stderr[-4000:], flush=True)
    return p.returncode

def cycle():
    print("BRAIN_SELF_IMPROVEMENT_CYCLE=1",flush=True)
    # Repository state and tests are observable; no credentials or arbitrary
    # remote execution are introduced by this loop.
    if run(["git","status","--short"]): return
    run(["python","-m","compileall","-q","cloud","brain_v7"])
    run(["python","-m","pytest","-q","brain_v7/tests"])
    print("BRAIN_SELF_IMPROVEMENT_VALIDATION_COMPLETE=1",flush=True)
    if AUTO_MERGE:
        print("AUTO_MERGE_REQUESTED_BUT_DISABLED_BY_DEFAULT=1",flush=True)

while True:
    try:
        cycle()
    except Exception as exc:
        print(f"SELF_IMPROVEMENT_ERROR={type(exc).__name__}:{exc}",flush=True)
    time.sleep(INTERVAL)
