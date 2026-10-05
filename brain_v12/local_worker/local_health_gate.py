#!/usr/bin/env python3
"""Unified health gate for the Brain local execution fabric."""
from __future__ import annotations
import json, time
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"brain6_artifacts"/"local_worker"
GUARDIAN=BASE/"guardian.json"
SUPERVISOR=BASE/"supervisor.json"
HEARTBEAT=BASE/"heartbeat.json"
QUEUED,RUNNING,COMPLETED,FAILED=(BASE/x for x in ("queued","running","completed","failed"))
EVIDENCE=ROOT/"brain6_artifacts"/"independence_gate"/"brain_local_verification.json"

def heartbeat_recent(max_age=60):
    try:
        p=json.loads(HEARTBEAT.read_text(encoding="utf-8"))
        ts=datetime.fromisoformat(str(p["timestamp"]))
        age=(datetime.now(timezone.utc)-ts).total_seconds()
        return age<=max_age
    except Exception:
        return False

def main():
    checks=[]
    guardian_present=GUARDIAN.exists()
    supervisor_present=SUPERVISOR.exists()
    checks.append(("guardian_or_supervisor_state",guardian_present or supervisor_present))
    if guardian_present:
        try:
            state=json.loads(GUARDIAN.read_text(encoding="utf-8"))
            checks.append(("guardian_ready",state.get("status")=="READY"))
        except Exception:
            checks.append(("guardian_ready",False))
    elif supervisor_present:
        try:
            state=json.loads(SUPERVISOR.read_text(encoding="utf-8"))
            checks.append(("supervisor_ready",state.get("status")=="READY"))
        except Exception:
            checks.append(("supervisor_ready",False))
    checks.append(("heartbeat_recent",heartbeat_recent()))
    for name,path in [("queued",QUEUED),("running",RUNNING),("completed",COMPLETED),("failed",FAILED)]:
        checks.append((f"directory_{name}",path.is_dir()))
    checks.append(("verification_evidence",EVIDENCE.exists()))
    ok=all(v for _,v in checks)
    report={"schema":"brain.local_execution_health.v2","status":"READY" if ok else "DEGRADED",
            "brain_runtime_independent":True,"github_runner_required":False,"windows_required":False,
            "authority_process":"guardian" if guardian_present else "legacy_supervisor",
            "checks":[{"name":n,"ok":v} for n,v in checks]}
    out=BASE/"health_gate.json"
    out.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))
    return 0 if ok else 1

if __name__=="__main__":
    raise SystemExit(main())
