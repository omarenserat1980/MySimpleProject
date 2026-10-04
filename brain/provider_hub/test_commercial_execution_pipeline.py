import pytest

from brain.provider_hub.containment import CommercialContainmentGate
from brain.provider_hub.decision_audit import DecisionAuditLog
from brain.provider_hub.policy_guard import CommercialPolicy, CommercialPolicyGuard
from brain.provider_hub.risk_gate import CommercialRiskGate
from brain.provider_hub.secure_human_approval import SecureHumanApprovalGate
from brain.provider_hub.commercial_execution_pipeline import CommercialExecutionPipeline


def make_pipeline():
    containment = CommercialContainmentGate()
    policy = CommercialPolicyGuard(CommercialPolicy(financial_action_authorized=True))
    risk = CommercialRiskGate()
    decisions = DecisionAuditLog()
    approvals = SecureHumanApprovalGate()
    return CommercialExecutionPipeline(containment, policy, risk, decisions, approvals), containment, approvals, decisions


def test_high_risk_blocks_without_human_approval():
    pipeline, _, _, _ = make_pipeline()
    result = pipeline.decide(
        "d1", "o1", "PAYOUT",
        financial_action=True, authorized=True, evidence_present=True,
        operational_risk=90, evidence_score=20, return_score=20,
    )
    assert result.allowed is False
    assert result.reason == "HUMAN_APPROVAL_REQUIRED"


def test_high_risk_requires_and_consumes_approval():
    pipeline, _, approvals, decisions = make_pipeline()
    approvals.request("a1", "o2", "PAYOUT", "HIGH")
    approvals.approve("a1")
    result = pipeline.decide(
        "d2", "o2", "PAYOUT",
        financial_action=True, authorized=True, evidence_present=True,
        operational_risk=90, evidence_score=20, return_score=20,
        approval_request_id="a1",
    )
    assert result.allowed is True
    assert result.reason == "ALLOWED"
    assert any(e.reason == "HUMAN_APPROVAL_CONSUMED" for e in decisions.for_order("o2"))


def test_containment_always_wins():
    pipeline, containment, _, _ = make_pipeline()
    containment.contain("o3", "SUSPICIOUS_ACTIVITY")
    result = pipeline.decide(
        "d3", "o3", "ACTION",
        financial_action=False, authorized=False, evidence_present=False,
        operational_risk=1, evidence_score=100, return_score=100,
    )
    assert result.allowed is False
    assert result.reason == "ORDER_CONTAINED"


def test_financial_action_without_evidence_is_blocked():
    pipeline, _, _, _ = make_pipeline()
    result = pipeline.decide(
        "d4", "o4", "CHARGE",
        financial_action=True, authorized=True, evidence_present=False,
        operational_risk=1, evidence_score=100, return_score=100,
    )
    assert result.allowed is False
