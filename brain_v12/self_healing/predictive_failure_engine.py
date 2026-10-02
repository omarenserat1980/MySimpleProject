#!/usr/bin/env python3
"""Predictive failure analysis for Brain self-healing.

This layer does not execute repairs. It inspects known evidence and current
runtime signals, predicts likely failure modes, and emits bounded preflight
checks so preventable failures can be caught before the main verification run.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / ".brain" / "state"
REPORT = STATE / "predictive_failure_report.json"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def check_import(name: str) -> dict:
    available = importlib.util.find_spec(name) is not None
    return {"name": f"dependency:{name}", "risk": "high", "predicted_failure": not available,
            "evidence": "available" if available else "module_not_installed"}


def check_gate_command() -> dict:
    path = ROOT / "brain_v12" / "self_healing" / "verification_gate.py"
    exists = path.is_file()
    return {"name": "verification-gate-present", "risk": "high",
            "predicted_failure": not exists, "evidence": str(path) if exists else "missing"}


def check_previous_gate_failure() -> dict:
    path = STATE / "verification_gate.json"
    if not path.is_file():
        return {"name": "previous-gate-failure", "risk": "medium",
                "predicted_failure": False, "evidence": "no_previous_report"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"name": "previous-gate-failure", "risk": "medium",
                "predicted_failure": True, "evidence": f"invalid_report:{exc}"}
    failed = [g.get("name") for g in data.get("gates", []) if not g.get("passed")]
    return {"name": "previous-gate-failure", "risk": "high" if failed else "low",
            "predicted_failure": bool(failed),
            "evidence": {"failed_gates": failed, "status": data.get("status")}}


def check_self_test_matrix() -> dict:
    cmd = [sys.executable, "-m", "brain_v12.self_healing.self_test_matrix"]
    try:
        p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=30)
        return {"name": "preflight:self-test-matrix", "risk": "high",
                "predicted_failure": p.returncode != 0,
                "exit_code": p.returncode,
                "evidence": (p.stdout + p.stderr)[-4000:]}
    except subprocess.TimeoutExpired:
        return {"name": "preflight:self-test-matrix", "risk": "high",
                "predicted_failure": True, "exit_code": 124, "evidence": "timeout"}


def predict() -> dict:
    checks = [
        check_import("httpx"),
        check_gate_command(),
        check_previous_gate_failure(),
        check_self_test_matrix(),
    ]
    risks = [c for c in checks if c["predicted_failure"]]
    return {
        "schema": "brain-predictive-failure/v1",
        "created_at": now(),
        "status": "RISK_PREDICTED" if risks else "PREFLIGHT_CLEAR",
        "predicted_failure_count": len(risks),
        "checks": checks,
        "required_action": "prevent_or_repair_before_main_verification" if risks else "proceed_to_verification",
    }


def main() -> int:
    STATE.mkdir(parents=True, exist_ok=True)
    report = predict()
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    # A prediction is not itself a repair failure; callers decide whether the
    # predicted risk has a safe preventive action.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
