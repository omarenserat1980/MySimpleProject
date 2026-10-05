#!/usr/bin/env python3
"""Evidence gate for Brain's local operational independence.

Runs the existing local integrity and real-worker self-tests as subprocesses
with GitHub credentials removed, then emits one durable proof report.
"""
from __future__ import annotations
import hashlib, json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

from platform_foundation.independence_contract import IndependenceContract

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "brain6_artifacts" / "independence_gate" / "independence_proof.json"


def run(cmd):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    for key in ("GITHUB_TOKEN", "GH_TOKEN", "GIT_ASKPASS"):
        env.pop(key, None)
    p = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    return {
        "command": cmd,
        "return_code": p.returncode,
        "passed": p.returncode == 0,
        "stdout": p.stdout[-20000:],
        "stderr": p.stderr[-12000:],
    }


def main():
    started = datetime.now(timezone.utc).isoformat()
    integrity = run([sys.executable, "tools/base_expansion_integrity.py"])
    worker = run([sys.executable, "tools/brain_local_worker_selftest.py"])
    authority = run([sys.executable, "-m", "pytest", "-q", "tests/test_authority_boundary_gate.py", "tests/test_independence_contract.py"])
    checks = {
        "base_expansion_integrity": integrity["passed"],
        "real_worker_execution": worker["passed"],
        "authority_boundary_negative_tests": authority["passed"],
        "github_credentials_removed": True,
        "network_dependency_for_gate": False,
    }
    # This gate proves local execution/recovery, not unrestricted autonomy.
    proof_allowed = all(checks.values())
    report = {
        "schema": "brain.independence_proof.v1",
        "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "status": "PROVEN_WITHIN_TEST_SCOPE" if proof_allowed else "NOT_PROVEN",
        "independence_claim_allowed": proof_allowed,
        "scope": {
            "local_execution": True,
            "queue_to_completed": worker["passed"],
            "restart_recovery": worker["passed"],
            "base_integrity": integrity["passed"],
            "external_github_required": False,
            "authority_boundary": authority["passed"],
        },
        "checks": checks,
        "evidence": {
            "integrity": integrity,
            "worker_selftest": worker,
            "authority_boundary": authority,
        },
        "limitations": [
            "This gate does not prove unrestricted autonomy.",
            "Authority proof is limited to the explicit negative/positive cases covered by tests/test_authority_boundary_gate.py.",
            "External integrations remain optional capabilities, not runtime requirements.",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    canonical = json.dumps(report, indent=2, ensure_ascii=False)
    OUT.write_text(canonical, encoding="utf-8")
    contract = IndependenceContract(OUT).evaluate()
    report["independence_contract"] = contract
    proof_allowed = proof_allowed and contract["allowed"]
    report["status"] = "PROVEN_WITHIN_TEST_SCOPE" if proof_allowed else "NOT_PROVEN"
    report["independence_claim_allowed"] = proof_allowed
    report["report_sha256"] = hashlib.sha256(OUT.read_bytes()).hexdigest()
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if proof_allowed else 1


if __name__ == "__main__":
    raise SystemExit(main())
