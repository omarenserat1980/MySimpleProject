from brain.provider_hub.commercial_ledger import CommercialLedger
from brain.provider_hub.commercial_state import CommercialOrderState
from brain.provider_hub.evidence import CommercialEvidenceGate
from brain.provider_hub.integrity_chain import IntegrityChain
from brain.provider_hub.reconciliation import CommercialReconciliationEngine


def test_consistent_order_passes():
    order = CommercialOrderState("o1", "PAYMENT_VERIFIED")
    ledger = CommercialLedger()
    ledger.record("e1", "o1", "NEW", "PAYMENT_VERIFIED", ("p1",))
    integrity = IntegrityChain()
    integrity.append("e1", "o1", "NEW", "PAYMENT_VERIFIED", ("p1",))
    report = CommercialReconciliationEngine(
        ledger, integrity, CommercialEvidenceGate()
    ).check(order)
    assert report.consistent is True
    assert report.issues == ()


def test_state_ledger_mismatch_is_detected():
    order = CommercialOrderState("o2", "REVENUE_REALIZED")
    ledger = CommercialLedger()
    ledger.record("e1", "o2", "NEW", "PAYMENT_VERIFIED", ("p1",))
    integrity = IntegrityChain()
    integrity.append("e1", "o2", "NEW", "PAYMENT_VERIFIED", ("p1",))
    report = CommercialReconciliationEngine(
        ledger, integrity, CommercialEvidenceGate()
    ).check(order)
    assert report.consistent is False
    assert "STATE_LEDGER_MISMATCH" in report.issues


def test_integrity_failure_is_detected():
    order = CommercialOrderState("o3", "PAYMENT_VERIFIED")
    ledger = CommercialLedger()
    ledger.record("e1", "o3", "NEW", "PAYMENT_VERIFIED", ("p1",))
    integrity = IntegrityChain()
    integrity.append("e1", "o3", "NEW", "PAYMENT_VERIFIED", ("p1",))
    integrity._entries[0] = integrity._entries[0].__class__(
        **{**integrity._entries[0].__dict__, "to_state": "COMPLETED"}
    )
    report = CommercialReconciliationEngine(
        ledger, integrity, CommercialEvidenceGate()
    ).check(order)
    assert report.consistent is False
    assert "INTEGRITY_CHAIN_INVALID" in report.issues
