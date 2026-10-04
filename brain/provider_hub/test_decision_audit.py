import pytest

from brain.provider_hub.decision_audit import DecisionAuditLog


def test_decision_is_recorded():
    log = DecisionAuditLog()
    event = log.record(
        "d1", "o1", "PAYMENT", False,
        "FINANCIAL_AUTHORIZATION_REQUIRED",
        evidence_refs=("p1",),
    )
    assert event.allowed is False
    assert log.for_order("o1")[0].reason == "FINANCIAL_AUTHORIZATION_REQUIRED"


def test_duplicate_decision_is_rejected():
    log = DecisionAuditLog()
    log.record("d1", "o1", "PAYMENT", False, "BLOCKED")
    with pytest.raises(ValueError, match="DUPLICATE_DECISION:d1"):
        log.record("d1", "o1", "PAYMENT", True, "AUTHORIZED")
