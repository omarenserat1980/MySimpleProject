from brain_v7.braincore_v2.revenue_target_orchestrator import (
    TargetCandidate,
    orchestrate,
    preparation_gate,
    rank_candidates,
)
from brain_v7.braincore_v2.revenue_target_engine import RevenueOutcome


def good(i="1"):
    return TargetCandidate(i, "Arabic product video", "short_video", 100, 2, .9, .9, .1, True)


def test_gate_requires_evidence():
    c = TargetCandidate("1", "x", "short_video", 100, 2, .2, .9, .1)
    assert preparation_gate(c) == "RESEARCH_REQUIRED"


def test_ranking_prefers_repeatable_economics():
    a = good("a")
    b = TargetCandidate("b", "b", "copy", 20, 2, .9, .9, .1)
    assert rank_candidates([b, a])[0].lead_id == "a"


def test_orchestrator_keeps_external_submission_gated():
    result = orchestrate(
        [good()],
        [RevenueOutcome("paid", 50, "PAID", "provider-ref")],
    )
    assert result["verified_revenue_usd"] == 50
    assert result["queue_count"] == 1
    assert result["external_submission_performed"] is False
    assert result["money_movement_performed"] is False
