import pytest

from economics.economic_memory import (
    EconomicObservation,
    Outcome,
    estimate,
    verified_payment_total,
)


def test_empty_memory_uses_neutral_prior():
    result = estimate([], "arabic_ai_evaluation")
    assert result.acceptance_probability == 0.5
    assert result.risk == 0.5
    assert result.observations == 0


def test_memory_learns_from_outcomes():
    observations = [
        EconomicObservation("arabic_ai_evaluation", Outcome.ACCEPTED, 2, 100),
        EconomicObservation("arabic_ai_evaluation", Outcome.REJECTED, 1, 100),
        EconomicObservation("arabic_ai_evaluation", Outcome.DELIVERED, 3, 100),
    ]
    result = estimate(observations, "arabic_ai_evaluation")
    assert result.acceptance_probability == 2 / 3
    assert result.risk == 1 / 3
    assert result.observations == 3


def test_unrelated_classes_are_ignored():
    observations = [
        EconomicObservation("video", Outcome.ACCEPTED, 2, 100),
        EconomicObservation("arabic_ai_evaluation", Outcome.REJECTED, 1, 20),
    ]
    result = estimate(observations, "arabic_ai_evaluation")
    assert result.observations == 1
    assert result.acceptance_probability == 0


def test_verified_payment_requires_evidence():
    with pytest.raises(ValueError):
        EconomicObservation(
            "video", Outcome.PAYMENT_VERIFIED, 1, 20, payment_amount=20
        )


def test_only_verified_payments_count_as_revenue_evidence():
    observations = [
        EconomicObservation("video", Outcome.DELIVERED, 1, 20, payment_amount=20),
        EconomicObservation(
            "video", Outcome.PAYMENT_VERIFIED, 1, 20,
            payment_amount=15, evidence_ref="payment-1"
        ),
    ]
    assert verified_payment_total(observations) == 15
