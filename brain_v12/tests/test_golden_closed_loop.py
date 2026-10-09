from brain_v12.brain.golden_closed_loop import CLOSED, REPAIR, SCHEMA, GoldenClosedLoop, TruthGate


def valid_evidence():
    return {
        "goal_verified": True,
        "evidence_verified": True,
        "execution_verified": True,
        "independent_verification": True,
        "cost_gate_ok": True,
        "rollback_ready": True,
    }


def test_truth_gate_fails_closed_on_missing_proof():
    result = GoldenClosedLoop().run({"goal_verified": True})
    assert result["schema"] == SCHEMA
    assert result["status"] == REPAIR
    assert result["closed"] is False
    assert result["repair_required"] is True
    assert "TRUTH_GATE_EVIDENCE_VERIFIED_FAILED" in result["reasons"]


def test_success_requires_cost_gate_and_rollback():
    evidence = valid_evidence()
    result = GoldenClosedLoop().run(evidence)
    assert result["status"] == CLOSED
    assert result["closed"] is True
    assert result["phase"] == "SEALED"
    assert result["next_action"] == "NONE"
    assert len(result["seal_sha256"]) == 64


def test_presealed_evidence_cannot_be_reclosed():
    evidence = valid_evidence()
    evidence["evidence_sealed"] = True
    result = TruthGate().evaluate(evidence)
    assert result.verified is False
    assert "TRUTH_GATE_EVIDENCE_ALREADY_SEALED" in result.reasons
