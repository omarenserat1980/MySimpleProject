from brain_v7.braincore_v2.revenue_target_engine import (
    RevenueOutcome,
    TARGET_USD,
    build_plan,
    target_status,
    verified_revenue,
)


def test_target_is_100k():
    assert TARGET_USD == 100_000.0


def test_only_verified_payments_count():
    outcomes = [
        RevenueOutcome("a", 1000, "PAID", "provider-ref"),
        RevenueOutcome("b", 9000, "EXPECTED", "proposal"),
        RevenueOutcome("c", 500, "PAID", ""),
    ]
    assert verified_revenue(outcomes) == 1000


def test_remaining_target():
    state = target_status([RevenueOutcome("a", 2500, "SETTLED", "ref")])
    assert state["verified_revenue_usd"] == 2500
    assert state["remaining_usd"] == 97500
    assert state["achieved"] is False


def test_plan_does_not_claim_execution():
    plan = build_plan()
    assert plan["verified_revenue_usd"] == 0
    assert plan["external_submission_performed"] is False
    assert plan["money_movement_performed"] is False
