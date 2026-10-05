import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_doctor_checks_independence_contract(tmp_path):
    proof = ROOT / "brain6_artifacts" / "independence_gate" / "independence_proof.json"
    backup = proof.read_text(encoding="utf-8") if proof.exists() else None
    proof.parent.mkdir(parents=True, exist_ok=True)
    proof.write_text(json.dumps({
        "status": "PROVEN_WITHIN_TEST_SCOPE",
        "independence_claim_allowed": True,
        "checks": {
            "base_expansion_integrity": True,
            "real_worker_execution": True,
            "authority_boundary_negative_tests": True,
            "github_credentials_removed": True,
            "network_dependency_for_gate": False,
        },
        "scope": {
            "local_execution": True,
            "queue_to_completed": True,
            "restart_recovery": True,
            "authority_boundary": True,
        },
        "report_sha256": "test",
    }), encoding="utf-8")
    try:
        result = subprocess.run(
            [sys.executable, "tools/brain_runtime_doctor.py"],
            cwd=ROOT, capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        report = json.loads(result.stdout)
        names = {item["name"] for item in report["checks"]}
        assert "independence_contract" in names
    finally:
        if backup is None:
            proof.unlink(missing_ok=True)
        else:
            proof.write_text(backup, encoding="utf-8")
