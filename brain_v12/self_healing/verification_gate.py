#!/usr/bin/env python3
"""Independent Brain verification gate."""
from __future__ import annotations
import importlib.util
import json, os, subprocess, sys
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
        p = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=timeout)
        return {
            "name": name, "command": command, "started_at": started,
            "finished_at": now(), "exit_code": p.returncode,
            "stdout": p.stdout[-12000:], "stderr": p.stderr[-12000:],
            "passed": p.returncode == 0,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "name": name, "command": command, "started_at": started,
            "finished_at": now(), "exit_code": 124,
            "stdout": (exc.stdout or "")[-12000:] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "")[-12000:] if isinstance(exc.stderr, str) else "",
            "passed": False, "error": "timeout",
        }
    except Exception as exc:
        return {
            "name": name, "command": command, "started_at": started,
            "finished_at": now(), "exit_code": 125,
            "stdout": "", "stderr": repr(exc), "passed": False,
        }

def optional_pytest(timeout: int) -> dict:
    started = now()
    if importlib.util.find_spec("pytest") is None:
        return {
            "name": "pytest",
            "command": [sys.executable, "-m", "pytest", "-q"],
            "started_at": started,
            "finished_at": now(),
            "exit_code": None,
            "stdout": "",
            "stderr": "pytest is not installed; optional gate skipped",
            "passed": True,
            "skipped": True,
        }
    return run("pytest", [sys.executable, "-m", "pytest", "-q"], timeout)

def main() -> int:
    timeout = int(os.getenv("BRAIN_GATE_TIMEOUT", "120"))
    gates = [
        ("compile", [sys.executable, "-m", "compileall", "-q", "brain_v12"]),
        # Run package modules so brain_v12 imports resolve consistently in CI.
        ("self-test", [sys.executable, "-m", "brain_v12.self_healing.self_test"]),
        ("self-test-matrix", [sys.executable, "-m", "brain_v12.self_healing.self_test_matrix"]),
        ("cloud-only-policy", [sys.executable, "-m", "brain_v12.self_healing.cloud_only_guard"]),
        ("completion-audit", [sys.executable, "brain_v12/self_healing/completion_audit.py"]),
        ("causal-evidence", [sys.executable, "-m", "brain_v12.causal.runtime_bridge"]),
    ]

    results = [run(name, command, timeout) for name, command in gates]

    if os.getenv("BRAIN_GATE_PYTEST", "0") == "1":
        results.append(optional_pytest(timeout))

    health = os.getenv("BRAIN_HEALTH_COMMAND", "").strip()
    if health:
        results.append(run("health", ["bash", "-lc", health], timeout))

    passed = all(item["passed"] for item in results)
    report = {
        "schema": "brain-verification-gate/v3",
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
        "failed_gates": [
            {
                "name": item["name"],
                "exit_code": item["exit_code"],
                "stdout": item["stdout"][-4000:],
                "stderr": item["stderr"][-4000:],
                "error": item.get("error"),
            }
            for item in results if not item["passed"]
        ],
    }, ensure_ascii=False))
    return 0 if passed else 1

if __name__ == "__main__":
    raise SystemExit(main())
