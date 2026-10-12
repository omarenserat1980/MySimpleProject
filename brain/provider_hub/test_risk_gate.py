import pytest

from brain.provider_hub.risk_gate import CommercialRiskGate


def test_low_risk_can_pass():
    gate = CommercialRiskGate()
    assessment = gate.assess(
        operational_risk=10, evidence_score=95, return_score=90
    )
    decision = gate.decide(
        assessment,
        authorized=True,
        contained=False,
        financial_action=False,
        evidence_present=False,
    )
    assert decision.allowed is True
    assert decision.reason == "RISK_ACCEPTABLE"


def test_high_risk_requires_review():
    gate = CommercialRiskGate()
    assessment = gate.assess(
        operational_risk=100, evidence_score=0, return_score=0
    )
    decision = gate.decide(
        assessment,
        authorized=True,
        contained=False,
        financial_action=False,
        evidence_present=False,
    )
    assert decision.allowed is False
    assert decision.reason == "HIGH_RISK_REQUIRES_REVIEW"


def test_risk_never_overrides_financial_evidence():
    gate = CommercialRiskGate()
    assessment = gate.assess(
        operational_risk=1, evidence_score=100, return_score=100
    )
    decision = gate.decide(
        assessment,
        authorized=True,
        contained=False,
        financial_action=True,
        evidence_present=False,
    )
    assert decision.allowed is False
    assert decision.reason == "FINANCIAL_EVIDENCE_REQUIRED"


def test_invalid_scores_are_rejected():
    with pytest.raises(ValueError, match="RISK_SCORE_OUT_OF_RANGE"):
        CommercialRiskGate().assess(
            operational_risk=101, evidence_score=50, return_score=50
        )
