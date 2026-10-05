import json
from pathlib import Path

import tools.brain_autonomy_status as status


def test_autonomy_status_requires_both_proof_and_live_authority(monkeypatch, tmp_path):
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
            "authority_boundary": True,
        },
    }), encoding="utf-8")
    monkeypatch.setattr(status, "PROOF", proof)
    monkeypatch.setattr(status.BrainExecutionAuthority, "readiness",
                        lambda self: {"ready": False, "reason": "offline"})
    result = status.evaluate()
    assert result["scoped_independence_proven"] is True
    assert result["live_brain_executor_ready"] is False
    assert result["AUTONOMOUS_WITHIN_AUTHORITY"] is False


def test_autonomy_status_is_true_only_with_live_authority(monkeypatch, tmp_path):
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
            "authority_boundary": True,
        },
    }), encoding="utf-8")
    monkeypatch.setattr(status, "PROOF", proof)
    monkeypatch.setattr(status.BrainExecutionAuthority, "readiness",
                        lambda self: {"ready": True})
    result = status.evaluate()
    assert result["AUTONOMOUS_WITHIN_AUTHORITY"] is True
