#!/usr/bin/env python3
"""Evidence gate for Brain's local operational independence.

Runs local integrity and worker self-tests with GitHub credentials removed,
then writes a durable, hash-checked proof report. This is scoped evidence,
not proof of unrestricted autonomy or OS-enforced network isolation.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from platform_foundation.independence_contract import (
    IndependenceContract,
    compute_report_sha256,
)

OUT = ROOT / "brain6_artifacts" / "independence_gate" / "independence_proof.json"
CREDENTIAL_KEYS = ("GITHUB_TOKEN", "GH_TOKEN", "GIT_ASKPASS")


def run(cmd):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    for key in CREDENTIAL_KEYS:
        env.pop(key, None)
    credentials_removed = all(not env.get(key) for key in CREDENTIAL_KEYS)
    p = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    return {
        "command": cmd,
        "return_code": p.returncode,
        "passed": p.returncode == 0,
        "github_credentials_removed_from_child_env": credentials_removed,
        "stdout": p.stdout[-20000:],
        "stderr": p.stderr[-12000:],
    }


def write_report(report):
    report["report_sha256"] = compute_report_sha256(report)
    OUT.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def main():
    started = datetime.now(timezone.utc).isoformat()
    integrity = run([sys.executable, "tools/base_expansion_integrity.py"])
    worker = run([sys.executable, "tools/brain_local_worker_selftest.py"])
    authority = run([
        sys.executable, "-m", "pytest", "-q",
        "tests/test_authority_boundary_gate.py",
        "tests/test_independence_contract.py",
    ])

    credentials_removed = all(
        result["github_credentials_removed_from_child_env"]
        for result in (integrity, worker, authority)
    )
    checks = {
        "base_expansion_integrity": integrity["passed"],
        "real_worker_execution": worker["passed"],
        "authority_boundary_negative_tests": authority["passed"],
        "github_credentials_removed": credentials_removed,
        # This describes the intended local-only gate contract; it is not a
        # claim that the runner was placed in an OS-enforced network namespace.
        "network_dependency_for_gate": False,
    }
    positive_checks = (
        "base_expansion_integrity",
        "real_worker_execution",
        "authority_boundary_negative_tests",
        "github_credentials_removed",
    )
    proof_allowed = (
        all(checks[name] is True for name in positive_checks)
        and checks["network_dependency_for_gate"] is False
    )

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
            "Authority proof is limited to explicit cases covered by tests/test_authority_boundary_gate.py.",
            "External integrations remain optional capabilities, not runtime requirements.",
            "network_dependency_for_gate records the local-only design assertion; OS-enforced network isolation is not verified by this script.",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)

    # The contract hash excludes the derived independence_contract field.
    # Finalize the claim, hash the report, evaluate it, then persist the result.
    write_report(report)
    contract = IndependenceContract(OUT).evaluate()
    if not contract.get("allowed", False):
        report["status"] = "NOT_PROVEN"
        report["independence_claim_allowed"] = False
    report["independence_contract"] = contract
    write_report(report)

    # Verify the exact final payload after its last write. Because the contract
    # field is excluded from the digest, adding the result does not alter it.
    final_contract = IndependenceContract(OUT).evaluate()
    report["independence_contract"] = final_contract
    if not final_contract.get("allowed", False):
        report["status"] = "NOT_PROVEN"
        report["independence_claim_allowed"] = False
    write_report(report)

    # One last read-only verification guards against serialization/hash drift.
    verified_contract = IndependenceContract(OUT).evaluate()
    digest_ok = json.loads(OUT.read_text(encoding="utf-8")).get("report_sha256") == compute_report_sha256(
        json.loads(OUT.read_text(encoding="utf-8"))
    )
    if not verified_contract.get("allowed", False) or not digest_ok:
        report["status"] = "NOT_PROVEN"
        report["independence_claim_allowed"] = False
        report["independence_contract"] = verified_contract
        write_report(report)

    print(OUT.read_text(encoding="utf-8"))
    final = json.loads(OUT.read_text(encoding="utf-8"))
    return 0 if final.get("status") == "PROVEN_WITHIN_TEST_SCOPE" and verified_contract.get("allowed") and digest_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
