import pytest

from brain.provider_hub.decision_audit import DecisionAuditLog
from brain.provider_hub.secure_human_approval import SecureHumanApprovalGate, AuditedSecureApprovalService


def test_approval_is_single_use():
    gate = SecureHumanApprovalGate()
    gate.request("a1", "o1", "ACTION", "HIGH")
    gate.approve("a1")
    gate.consume("a1")
    with pytest.raises(RuntimeError, match="APPROVAL_ALREADY_CONSUMED:a1"):
        gate.consume("a1")


def test_unapproved_cannot_be_consumed():
    gate = SecureHumanApprovalGate()
    gate.request("a2", "o2", "ACTION", "HIGH")
    with pytest.raises(RuntimeError, match="HUMAN_APPROVAL_REQUIRED:a2"):
        gate.consume("a2")


def test_expired_approval_is_blocked():
    gate = SecureHumanApprovalGate(ttl_seconds=1)
    gate.request("a3", "o3", "ACTION", "HIGH")
    gate._secure["a3"] = gate._secure["a3"].__class__(
        "a3", "o3", "ACTION", "HIGH", "2000-01-01T00:00:00+00:00", "2000-01-01T00:00:01+00:00"
    )
    with pytest.raises(RuntimeError, match="APPROVAL_EXPIRED:a3"):
        gate.approve("a3")


def test_consumption_is_audited():
    gate = SecureHumanApprovalGate()
    decisions = DecisionAuditLog()
    gate.request("a4", "o4", "ACTION", "HIGH")
    gate.approve("a4")
    AuditedSecureApprovalService(gate, decisions).consume_for_action("a4", "d4")
    assert decisions.for_order("o4")[0].reason == "HUMAN_APPROVAL_CONSUMED"
