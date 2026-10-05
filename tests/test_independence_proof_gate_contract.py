import json
from pathlib import Path

from platform_foundation.independence_contract import IndependenceContract


def test_contract_rejects_proof_without_required_authority_scope(tmp_path):
    proof = tmp_path / "independence_proof.json"
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
            "authority_boundary": False,
        },
    }), encoding="utf-8")
    result = IndependenceContract(proof).evaluate()
    assert result["allowed"] is False
    assert result["reason"] == "scope_insufficient"
