import json

from platform_foundation.independence_contract import IndependenceContract


def write_report(tmp_path, **overrides):
    report = {
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
        "report_sha256": "evidence",
    }
    report.update(overrides)
    path = tmp_path / "independence_proof.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    return path


def test_contract_allows_only_proven_scope(tmp_path):
    result = IndependenceContract(write_report(tmp_path)).evaluate()
    assert result["allowed"] is True
    assert result["reason"] == "scoped_independence_proven"


def test_contract_fails_closed_when_proof_missing(tmp_path):
    result = IndependenceContract(tmp_path / "missing.json").evaluate()
    assert result == {"allowed": False, "reason": "proof_missing"}


def test_contract_rejects_false_claim(tmp_path):
    path = write_report(tmp_path, independence_claim_allowed=False)
    result = IndependenceContract(path).evaluate()
    assert result["allowed"] is False
    assert result["reason"] == "claim_not_allowed"


def test_contract_rejects_missing_authority_proof(tmp_path):
    path = write_report(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["scope"]["authority_boundary"] = False
    path.write_text(json.dumps(data), encoding="utf-8")
    result = IndependenceContract(path).evaluate()
    assert result["allowed"] is False
    assert result["reason"] == "authority_boundary_not_proven"


def test_contract_rejects_network_dependency(tmp_path):
    path = write_report(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["checks"]["network_dependency_for_gate"] = True
    path.write_text(json.dumps(data), encoding="utf-8")
    result = IndependenceContract(path).evaluate()
    assert result["allowed"] is False
    assert result["reason"] == "checks_failed"
