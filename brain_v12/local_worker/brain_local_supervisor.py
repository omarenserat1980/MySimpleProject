#!/usr/bin/env python3
"""Local Brain worker supervisor: durable health/heartbeat, no external runner required."""
from __future__ import annotations
import json, os, subprocess, sys, time
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "brain6_artifacts" / "local_worker" / "supervisor.json"
WORKER = ROOT / "brain_v12" / "local_worker" / "brain_local_worker.py"
HEARTBEAT = max(1.0, float(os.environ.get("BRAIN_LOCAL_SUPERVISOR_HEARTBEAT_SECONDS", "10")))

def now():
    return datetime.now(timezone.utc).isoformat()

def write(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(STATE)

def main():
    proc = None
    restart_count = 0
    while True:
        if proc is None or proc.poll() is not None:
            if proc is not None:
                restart_count += 1
            proc = subprocess.Popen([sys.executable, str(WORKER)], cwd=ROOT)
        status = {
            "schema": "brain.local_worker_supervisor.v1",
            "supervisor": "brain-local-supervisor",
            "worker_id": os.environ.get("BRAIN_WORKER_ID", "brain-local-01"),
            "status": "READY" if proc.poll() is None else "DEGRADED",
            "worker_pid": proc.pid,
            "restart_count": restart_count,
            "heartbeat_at": now(),
            "github_runner_required": False,
            "windows_required": False,
        }
        write(status)
        time.sleep(HEARTBEAT)

if __name__ == "__main__":
    raise SystemExit(main())
