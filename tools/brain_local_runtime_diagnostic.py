#!/usr/bin/env python3
"""Diagnose every layer of the local Brain executor without changing state."""
from __future__ import annotations
import json, os, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HB = ROOT/"brain6_artifacts/local_worker/heartbeat.json"
SUP = ROOT/"brain6_artifacts/local_worker/supervisor.json"
GUARD = ROOT/"brain6_artifacts/local_worker/guardian.json"
LOG = ROOT/"brain6_artifacts/local_worker/supervisor.log"
GUARD_LOG = ROOT/"brain6_artifacts/local_worker/guardian.log"

def age(path):
    try:
        p=json.loads(path.read_text(encoding="utf-8"))
        ts=datetime.fromisoformat(str(p["timestamp"]))
        return round((datetime.now(timezone.utc)-ts).total_seconds(),3),p
    except Exception as e:
        return None,{"error":f"{type(e).__name__}:{e}"}

def pgrep(pattern):
    try:
        out=subprocess.check_output(["pgrep","-af",pattern],text=True,stderr=subprocess.DEVNULL)
        return out.splitlines()
    except Exception:
        return []

def tail(path,n=80):
    try:return path.read_text(encoding="utf-8",errors="replace").splitlines()[-n:]
    except Exception:return []

def main():
    hb_age,hb=age(HB)
    report={
      "schema":"brain.local_runtime_diagnostic.v1",
      "python":sys.version.split()[0],
      "root":str(ROOT),
      "heartbeat":{"age_seconds":hb_age,"payload":hb},
      "supervisor":{"state":json.loads(SUP.read_text()) if SUP.exists() else None},
      "guardian":{"state":json.loads(GUARD.read_text()) if GUARD.exists() else None},
      "processes":{
        "supervisor":pgrep("brain_local_supervisor"),
        "guardian":pgrep("brain_local_guardian"),
        "worker":pgrep("brain_local_worker"),
      },
      "logs":{"supervisor":tail(LOG),"guardian":tail(GUARD_LOG)},
      "checks":{
        "heartbeat_file_exists":HB.exists(),
        "heartbeat_fresh":hb_age is not None and hb_age <= 30,
        "worker_process_seen":bool(pgrep("brain_local_worker")),
        "supervisor_process_seen":bool(pgrep("brain_local_supervisor")),
      }
    }
    print(json.dumps(report,indent=2,ensure_ascii=False))
    return 0 if report["checks"]["heartbeat_fresh"] else 1
if __name__=="__main__": raise SystemExit(main())
