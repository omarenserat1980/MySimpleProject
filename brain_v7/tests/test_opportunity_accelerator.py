from brain_v7.braincore_v2.opportunity_accelerator import (
    AccelerationCandidate,
    build_parallel_plan,
    freshness_hours,
    rank_for_speed,
)


def test_speed_ranking_prefers_fast_economic_candidate():
    rows = rank_for_speed([
        AccelerationCandidate("slow", "Slow", "product_copy", 50, 5, .9, .9, .1, .1, 48),
        AccelerationCandidate("fast", "Fast", "product_copy", 5, .25, .9, .9, .1, .1, 1),
    ])
    assert rows[0]["lead_id"] == "fast"


def test_evidence_gate_prevents_submission():
    rows = rank_for_speed([
        AccelerationCandidate("x", "X", "short_video", 10, 1, .2, .9, .1, .1, 1),
    ])
    assert rows[0]["gate"] == "RESEARCH_REQUIRED"


def test_parallel_plan_is_bounded():
    candidates = [
        AccelerationCandidate(str(i), str(i), "product_copy", 5, .5, .9, .9, .1, .1, 1)
        for i in range(10)
    ]
    plan = build_parallel_plan(candidates, lanes=3)
    assert len(plan["parallel_candidates"]) == 3
    assert plan["execution_requires_user_submission"] is True
    assert plan["realized_profit_jod"] == 0.0


def test_freshness_hours_accepts_epoch():
    assert freshness_hours(0) is not None
