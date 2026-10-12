import pytest

from brain.provider_hub.decision_audit import DecisionAuditLog
from brain.provider_hub.human_approval import HumanApprovalGate
from brain.provider_hub.audited_human_approval import AuditedHumanApprovalGate


def test_approval_is_bound_to_decision_audit():
    approvals = HumanApprovalGate()
    decisions = DecisionAuditLog()
    approvals.request("a1", "o1", "IRREVERSIBLE_ACTION", "HIGH_RISK")
    result = AuditedHumanApprovalGate(approvals, decisions).approve("a1", "d1")
    assert result.approved is True
    event = decisions.for_order("o1")[0]
    assert event.reason == "HUMAN_APPROVAL_GRANTED"
    assert event.metadata["approval_request_id"] == "a1"


def test_duplicate_decision_id_prevents_replay():
    approvals = HumanApprovalGate()
    decisions = DecisionAuditLog()
    approvals.request("a2", "o2", "ACTION", "REVIEW")
    gate = AuditedHumanApprovalGate(approvals, decisions)
    gate.approve("a2", "d2")
    with pytest.raises(ValueError, match="DUPLICATE_DECISION:d2"):
        gate.approve("a2", "d2")
