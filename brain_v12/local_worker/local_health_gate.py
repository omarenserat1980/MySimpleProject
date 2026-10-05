#!/usr/bin/env python3
"""Unified health gate for the Brain local execution fabric."""
from __future__ import annotations
import json, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "brain6_artifacts" / "local_worker"
SUPERVISOR = BASE / "supervisor.json"
QUEUED = BASE / "queued"
RUNNING = BASE / "running"
COMPLETED = BASE / "completed"
FAILED = BASE / "failed"
EVIDENCE = ROOT / "brain6_artifacts" / "independence_gate" / "brain_local_verification.json"

def main():
    checks = []
    checks.append(("supervisor_state", SUPERVISOR.exists()))
    if SUPERVISOR.exists():
        try:
            state = json.loads(SUPERVISOR.read_text(encoding="utf-8"))
            checks.append(("supervisor_ready", state.get("status") == "READY"))
            checks.append(("heartbeat_recent", time.time() - __import__("datetime").datetime.fromisoformat(
                state["heartbeat_at"].replace("Z", "+00:00")).timestamp() < 60))
        except Exception:
            checks.extend([("supervisor_ready", False), ("heartbeat_recent", False)])
    for name, path in [("queued", QUEUED), ("running", RUNNING),
                       ("completed", COMPLETED), ("failed", FAILED)]:
        checks.append((f"directory_{name}", path.is_dir()))
    checks.append(("verification_evidence", EVIDENCE.exists()))

    ok = all(value for _, value in checks)
    report = {
        "schema": "brain.local_execution_health.v1",
        "status": "READY" if ok else "DEGRADED",
        "brain_runtime_independent": True,
        "github_runner_required": False,
        "windows_required": False,
        "checks": [{"name": n, "ok": v} for n, v in checks],
    }
    out = BASE / "health_gate.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
