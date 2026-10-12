from brain_v12.economics.economic_control import CausalChain, EconomicBudget, RevenueAttribution
from brain_v12.economics.economic_control_plane import (
    evaluate_control,
    settle_verified_revenue,
    validate_attribution,
)
from brain_v12.economics.economic_governor import EconomicSignal, GovernorAction
from brain_v12.economics.revenue_gate import PaymentEvidence


def valid_evidence(amount=0.10):
    return PaymentEvidence(
        evidence_id="ev-control-1",
        opportunity_id="opp-control-1",
        amount=amount,
        currency="USD",
        received_at="2026-10-08T02:00:00Z",
        proof_ref="payment://verified/control-1",
    )


def test_control_plane_keeps_unverified_revenue_out():
    result = evaluate_control(
        signal=EconomicSignal(True, 10, 1, 0.1),
        budget=EconomicBudget(2, 2, 0.5),
        evidence=PaymentEvidence(
            "bad", "opp-control-1", 0.10, "USD",
            "2026-10-08T02:00:00Z", ""
        ),
    )
    assert result.governor.action == GovernorAction.ALLOW
    assert result.evidence.valid is False


def test_control_plane_settles_only_valid_proof():
    evidence = valid_evidence()
    result = evaluate_control(
        signal=EconomicSignal(True, 10, 1, 0.1),
        budget=EconomicBudget(2, 2, 0.5),
        evidence=evidence,
    )
    snapshot = settle_verified_revenue(
        revenue_event_id="rev-control-1",
        evidence_result=result.evidence,
        causality=CausalChain(
            "opp-control-1", "app-1", "task-1", "delivery-1", "ev-control-1"
        ),
    )
    assert snapshot.confirmed_revenue == 0.10


def test_invalid_attribution_is_rejected():
    try:
        validate_attribution(
            RevenueAttribution("rev", "opp", "", "channel", 1, "USD")
        )
        assert False
    except ValueError:
        assert True
