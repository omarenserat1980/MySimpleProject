import pytest

from brain.provider_hub.audit import ProviderAuditLog
from brain.provider_hub.containment import CommercialContainmentGate
from brain.provider_hub.decision_audit import DecisionAuditLog
from brain.provider_hub.policy_guard import CommercialPolicyGuard, CommercialPolicy
from brain.provider_hub.audited_action_gate import AuditedCommercialActionGate


def make(authorized=False):
    return AuditedCommercialActionGate(
        CommercialPolicyGuard(
            CommercialPolicy(financial_action_authorized=authorized)
        ),
        CommercialContainmentGate(),
        DecisionAuditLog(),
    )


def test_blocked_decision_is_audited():
    gate = make()
    result = gate.check(
        decision_id="d1",
        order_id="o1",
        action="PAYMENT",
        financial_action=True,
        evidence_present=True,
    )
    assert result.allowed is False
    assert result.decision_id == "d1"


def test_allowed_decision_is_audited():
    gate = make(True)
    result = gate.check(
        decision_id="d2",
        order_id="o2",
        action="PAYMENT",
        financial_action=True,
        evidence_present=True,
        evidence_refs=("p1",),
    )
    assert result.allowed is True


def test_duplicate_decision_id_blocks_replay():
    gate = make(True)
    args = dict(
        decision_id="d3", order_id="o3", action="PAYMENT",
        financial_action=True, evidence_present=True,
    )
    gate.check(**args)
    with pytest.raises(ValueError, match="DUPLICATE_DECISION:d3"):
        gate.check(**args)
