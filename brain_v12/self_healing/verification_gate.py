#!/usr/bin/env python3
"""Independent Brain verification gate.

This is deliberately stricter than a workflow-green signal. It runs the
available deterministic gates and emits durable evidence. A non-zero result
means VERIFIED_COMPLETED must not be emitted by higher-level supervisors.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / ".brain" / "state"
EVIDENCE = STATE / "verification_gate.json"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(name: str, command: list[str], timeout: int) -> dict:
    started = now()
    try:
        p = subprocess.run(
            command, cwd=ROOT, text=True, capture_output=True, timeout=timeout
        )
        return {
            "name": name,
            "command": command,
            "started_at": started,
            "finished_at": now(),
            "exit_code": p.returncode,
            "stdout": p.stdout[-12000:],
            "stderr": p.stderr[-12000:],
            "passed": p.returncode == 0,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "name": name,
            "command": command,
            "started_at": started,
            "finished_at": now(),
            "exit_code": 124,
            "stdout": (exc.stdout or "")[-12000:] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "")[-12000:] if isinstance(exc.stderr, str) else "",
            "passed": False,
            "error": "timeout",
        }
    except Exception as exc:
        return {
            "name": name,
            "command": command,
            "started_at": started,
            "finished_at": now(),
            "exit_code": 125,
            "stdout": "",
            "stderr": repr(exc),
            "passed": False,
        }


def main() -> int:
    timeout = int(os.getenv("BRAIN_GATE_TIMEOUT", "120"))
    gates = [
        ("compile", [sys.executable, "-m", "compileall", "-q", "brain_v12"]),
        ("self-test", [sys.executable, "brain_v12/self_healing/self_test.py"]),
        ("cloud-only-policy", [sys.executable, "brain_v12/self_healing/cloud_only_guard.py"]),
        ("completion-audit", [sys.executable, "brain_v12/self_healing/completion_audit.py"]),\n        ("causal-evidence", [sys.executable, "brain_v12/causal/runtime_bridge.py"]),
    ]
    if os.getenv("BRAIN_GATE_PYTEST", "1") == "1":
        gates.append(("pytest", [sys.executable, "-m", "pytest", "-q"]))
    health = os.getenv("BRAIN_HEALTH_COMMAND", "").strip()
    if health:
        gates.append(("health", ["bash", "-lc", health]))

    results = [run(name, command, timeout) for name, command in gates]
    passed = all(item["passed"] for item in results)
    report = {
        "schema": "brain-verification-gate/v2",
        "status": "VERIFIED" if passed else "FAILED",
        "verified_completed_allowed": passed,
        "created_at": now(),
        "gates": results,
        "health_command_configured": bool(os.getenv("BRAIN_HEALTH_COMMAND", "").strip()),
    }
    STATE.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "verified_completed_allowed": passed,
        "evidence": str(EVIDENCE),
    }, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
