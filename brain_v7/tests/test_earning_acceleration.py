from brain_v7.braincore_v2.earning_acceleration import (
    batch_report,
    candidate_from_lead,
    execution_gate,
    proposal_for,
    rank_candidates,
)


def test_candidate_scoring_and_profit_claim_are_separate():
    lead = {
        "lead_id": "abc",
        "title": "Arabic product video",
        "service": "short_video",
        "offered_jod": 25,
        "effort_hours": 1,
        "fit": 0.9,
        "evidence": 0.9,
        "friction": 0.1,
        "risk": 0.0,
    }
    c = candidate_from_lead(lead)
    assert c is not None
    assert c.expected_hourly_jod == 25
    assert c.score > 0
    report = batch_report([lead])
    assert report["candidate_count"] == 1
    assert report["realized_profit_jod"] == 0.0
    assert report["profit_status"] == "NO_VERIFIED_PAYMENT"


def test_rank_prefers_economic_and_evidence_quality():
    leads = [
        {
            "lead_id": "a", "title": "A", "service": "short_video",
            "offered_jod": 50, "effort_hours": 2,
            "fit": 0.9, "evidence": 0.9, "friction": 0.1, "risk": 0.0,
        },
        {
            "lead_id": "b", "title": "B", "service": "product_copy",
            "offered_jod": 10, "effort_hours": 2,
            "fit": 0.5, "evidence": 0.5, "friction": 0.5, "risk": 0.0,
        },
    ]
    assert rank_candidates(leads)[0]["lead_id"] == "a"


def test_execution_gate_requires_evidence():
    candidate = {
        "fit": 0.9, "evidence": 0.2, "risk": 0.0,
        "service": "short_video",
    }
    assert execution_gate(candidate)["status"] == "RESEARCH_REQUIRED"


def test_ready_still_requires_user_submission():
    candidate = {"fit": 0.9, "evidence": 0.9, "risk": 0.0}
    result = execution_gate(candidate)
    assert result["status"] == "READY_FOR_USER_SUBMISSION"
    assert result["requires_user_submission"] is True


def test_proposal_is_generated_without_sending():
    proposal = proposal_for({"service": "short_video"})
    assert "Hello" in proposal
    assert "Best regards" in proposal
