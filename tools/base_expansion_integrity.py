from __future__ import annotations

import json
import os
import subprocess
import sys
import hashlib
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
    "tests/test_authority_boundary_gate.py",
    "tests/test_independence_contract.py",
        "tests/test_brain_autonomy_status.py",
        "tests/test_brain_autonomy_gate.py",
]


def run() -> dict:
    started = datetime.now(timezone.utc).isoformat()
    cmd = [sys.executable, "-m", "pytest", "-q", *TESTS]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env.pop("GITHUB_TOKEN", None)
    env.pop("GH_TOKEN", None)
    env.pop("GIT_ASKPASS", None)
    proc = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    finished = datetime.now(timezone.utc).isoformat()

    report = {
        "schema": "brain.base_expansion_integrity.v1",
        "started_at": started,
        "finished_at": finished,
        "command": cmd,
        "test_count": len(TESTS),
        "return_code": proc.returncode,
        "status": "PASS" if proc.returncode == 0 else "FAIL",
        "execution_evidence": "LOCAL_PROCESS_EXECUTION_REQUIRED",
        "independence_claim_allowed": False,
        "independence_claim_reason": (
            "A passing verification suite is evidence of implementation correctness; "
            "it is not by itself proof of live Brain autonomy."
        ),
        "stdout": proc.stdout[-20000:],
        "stderr": proc.stderr[-12000:],
        "network_dependency": False,
        "github_credentials_removed": True,
        "report_sha256": None,
    }

    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    unsigned = json.dumps(report, indent=2, ensure_ascii=False)
    ARTIFACT.write_text(unsigned, encoding="utf-8")
    report["report_sha256"] = hashlib.sha256(ARTIFACT.read_bytes()).hexdigest()
    ARTIFACT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return report


if __name__ == "__main__":
    raise SystemExit(0 if run()["status"] == "PASS" else 1)
