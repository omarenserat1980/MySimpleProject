import pytest

from brain.provider_hub.audit import ProviderAuditLog
from brain.provider_hub.containment import CommercialContainmentGate
from brain.provider_hub.decision_audit import DecisionAuditLog
from brain.provider_hub.policy_guard import CommercialPolicyGuard, CommercialPolicy
from brain.provider_hub.risk_gate import CommercialRiskGate
from brain.provider_hub.decision_orchestrator import CommercialDecisionOrchestrator


def make(authorized=True):
    return CommercialDecisionOrchestrator(
        CommercialPolicyGuard(CommercialPolicy(financial_action_authorized=authorized)),
        CommercialContainmentGate(),
        CommercialRiskGate(),
        DecisionAuditLog(),
    )


def test_orchestrator_allows_safe_authorized_action():
    result = make().decide(
        decision_id="d1", order_id="o1", action="SERVICE",
        financial_action=False, evidence_present=False,
        operational_risk=10, evidence_score=95, return_score=90,
    )
    assert result.allowed is True
    assert result.reason == "RISK_ACCEPTABLE"
    assert result.risk_level == "LOW"


def test_policy_blocks_before_risk_can_allow():
    result = make(False).decide(
        decision_id="d2", order_id="o2", action="PAYMENT",
        financial_action=True, evidence_present=True,
        operational_risk=1, evidence_score=100, return_score=100,
    )
    assert result.allowed is False
    assert result.reason == "FINANCIAL_AUTHORIZATION_REQUIRED"


def test_financial_evidence_gate_cannot_be_overridden():
    result = make().decide(
        decision_id="d3", order_id="o3", action="PAYMENT",
        financial_action=True, evidence_present=False,
        operational_risk=1, evidence_score=100, return_score=100,
    )
    assert result.allowed is False
    assert result.reason == "FINANCIAL_EVIDENCE_REQUIRED"


def test_high_risk_requires_review():
    result = make().decide(
        decision_id="d4", order_id="o4", action="SERVICE",
        financial_action=False, evidence_present=False,
        operational_risk=100, evidence_score=0, return_score=0,
    )
    assert result.allowed is False
    assert result.reason == "HIGH_RISK_REQUIRES_REVIEW"
