"""Autonomous software factory for authorized Brain-owned workloads."""
from __future__ import annotations
import json, os, subprocess, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INTERVAL=int(os.getenv("BRAIN_SOFTWARE_FACTORY_INTERVAL_SECONDS","1800"))

def run(cmd, timeout=900):
    p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,timeout=timeout)
    print(json.dumps({"event":"software_factory_command","cmd":cmd,"rc":p.returncode,
                      "stdout":p.stdout[-3000:],"stderr":p.stderr[-3000:]},ensure_ascii=False),flush=True)
    return p.returncode

def cycle():
    print("BRAIN_SOFTWARE_FACTORY_CYCLE=1",flush=True)
    checks=[
        ["python","-m","compileall","-q","cloud","brain_v7"],
        ["python","-m","pytest","-q","brain_v7/tests"],
    ]
    for cmd in checks:
        if run(cmd):
            print("BRAIN_SOFTWARE_FACTORY_GATE=FAIL",flush=True)
            return
    print("BRAIN_SOFTWARE_FACTORY_GATE=PASS",flush=True)

while True:
    try:
        cycle()
    except Exception as exc:
        print(f"BRAIN_SOFTWARE_FACTORY_ERROR={type(exc).__name__}:{exc}",flush=True)
    time.sleep(INTERVAL)
