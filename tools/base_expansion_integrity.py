from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "brain6_artifacts" / "base_expansion" / "integrity_report.json"

TESTS = [
    "tests/test_executor_pool.py",
    "tests/test_local_worker_recovery_e2e.py",
    "tests/test_local_health_gate.py",
    "tests/test_capability_registry.py",
    "tests/test_phase_18_19_gate.py",
    "tests/test_phase_20_gate.py",
    "tests/test_phase_21_gate.py",
    "tests/test_phase_22_gate.py",
    "tests/test_audit_chain_persistence.py",
    "tests/test_task_lease_fencing.py",
    "tests/test_idempotency_and_concurrent_claim.py",
]


def run() -> dict:
    started = datetime.now(timezone.utc).isoformat()
    cmd = [sys.executable, "-m", "pytest", "-q", *TESTS]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    finished = datetime.now(timezone.utc).isoformat()

    report = {
        "schema": "brain.base_expansion_integrity.v1",
        "started_at": started,
        "finished_at": finished,
        "command": cmd,
        "test_count": len(TESTS),
        "return_code": proc.returncode,
        "status": "PASS" if proc.returncode == 0 else "FAIL",
        "independence_claim_allowed": False,
        "independence_claim_reason": (
            "A passing verification suite is evidence of implementation correctness; "
            "it is not by itself proof of live Brain autonomy."
        ),
        "stdout": proc.stdout[-20000:],
        "stderr": proc.stderr[-12000:],
    }

    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return report


if __name__ == "__main__":
    raise SystemExit(0 if run()["status"] == "PASS" else 1)
