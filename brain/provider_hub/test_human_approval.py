import pytest

from brain.provider_hub.human_approval import HumanApprovalGate


def test_high_risk_action_requires_approval():
    gate = HumanApprovalGate()
    gate.request("a1", "o1", "IRREVERSIBLE_ACTION", "HIGH_RISK")
    with pytest.raises(RuntimeError, match="HUMAN_APPROVAL_REQUIRED:a1"):
        gate.assert_approved("a1")


def test_explicit_approval_allows_continuation():
    gate = HumanApprovalGate()
    gate.request("a2", "o2", "FINANCIAL_ACTION", "IRREVERSIBLE")
    gate.approve("a2")
    gate.assert_approved("a2")
    assert gate.is_approved("a2") is True


def test_duplicate_request_is_rejected():
    gate = HumanApprovalGate()
    gate.request("a3", "o3", "ACTION", "REVIEW")
    with pytest.raises(ValueError, match="DUPLICATE_APPROVAL_REQUEST:a3"):
        gate.request("a3", "o3", "ACTION", "REVIEW")


def test_unknown_request_cannot_be_approved():
    gate = HumanApprovalGate()
    with pytest.raises(KeyError, match="UNKNOWN_APPROVAL_REQUEST:a4"):
        gate.approve("a4")
