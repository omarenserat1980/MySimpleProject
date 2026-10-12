from brain_v12.economics.control_api import ControlInput, evaluate_control_path


def test_control_api_rejects_duplicate_evidence():
    item = ControlInput(
        opportunity_id="opp-api-1",
        evidence_id="ev-api-1",
        amount=0.10,
        currency="USD",
        received_at="2026-10-08T02:00:00Z",
        proof_ref="payment://verified/api-1",
        verified=True,
        expected_value=2,
        execution_cost=1,
        risk_score=0.1,
        time_budget_hours=2,
        retry_budget=2,
        risk_budget=0.5,
        existing_evidence_ids=["ev-api-1"],
    )
    result = evaluate_control_path(item)
    assert result["evidence"]["valid"] is False
    assert result["revenue_claimed"] is False


def test_control_api_never_claims_revenue():
    item = ControlInput(
        opportunity_id="opp-api-2",
        evidence_id="ev-api-2",
        amount=0.10,
        currency="USD",
        received_at="2026-10-08T02:00:00Z",
        proof_ref="payment://verified/api-2",
        verified=True,
        expected_value=2,
        execution_cost=1,
        risk_score=0.1,
        time_budget_hours=2,
        retry_budget=2,
        risk_budget=0.5,
    )
    result = evaluate_control_path(item)
    assert result["evidence"]["valid"] is True
    assert result["revenue_claimed"] is False
    assert result["side_effects"] is False
