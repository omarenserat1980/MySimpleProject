from brain_v7.braincore_v2.opportunity_autopilot import (
    OpportunityPlan,
    autopilot_snapshot,
    execution_gate,
    plan_from_lead,
)


def make_plan(**kwargs):
    data = {
        "title": "Arabic product video",
        "service": "short_video",
        "offered_jod": 25,
        "effort_hours": 1,
        "freshness_hours": 2,
        "evidence_score": 0.9,
        "fit_score": 0.9,
        "risk_score": 0.1,
        "local_execution": True,
        "api_delivery_possible": True,
    }
    data.update(kwargs)
    return plan_from_lead(data)


def test_priority_rewards_speed_and_evidence():
    p = make_plan()
    assert p.speed_value == 25
    assert p.priority > 30


def test_weak_evidence_blocks():
    result = execution_gate(make_plan(evidence_score=0.2))
    assert result["status"] == "BLOCKED"
    assert "INSUFFICIENT_EVIDENCE" in result["blockers"]


def test_preparation_can_be_ready_without_submission():
    p = make_plan()
    result = execution_gate(p, artifact_ready=True, external_authorized=False)
    assert result["status"] == "READY_TO_PREPARE"
    assert result["submission_performed"] is False


def test_autopilot_never_claims_profit():
    result = autopilot_snapshot([{
        "title": "Test",
        "service": "product_copy",
        "offered_jod": 10,
        "effort_hours": 0.5,
        "evidence_score": 0.9,
        "fit_score": 0.9,
        "risk_score": 0.1,
    }])
    assert result["realized_profit_jod"] == 0.0
    assert result["profit_status"] == "NO_VERIFIED_PAYMENT"
    assert result["external_side_effects_performed"] is False
