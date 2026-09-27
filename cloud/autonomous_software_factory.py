"""Autonomous software factory cycle for authorized Brain-owned workloads."""
from __future__ import annotations
import json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

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
            return 1
    print("BRAIN_SOFTWARE_FACTORY_GATE=PASS",flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(cycle())
