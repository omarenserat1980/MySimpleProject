from brain.provider_hub.evidence import CommercialEvidenceGate, Evidence
from brain.provider_hub.payment_guard import PaymentIdempotencyGuard
from brain.provider_hub.payment_verification import EvidenceBoundPaymentService


def ev(order="o1"):
    return Evidence(
        evidence_id="pay-1",
        evidence_type="PAYMENT_VERIFICATION",
        order_id=order,
        source="test-provider",
        reference="txn-123",
        observed_at="2026-10-04T00:00:00Z",
        payload={"status": "paid"},
    )


def test_missing_evidence_blocks_verification():
    s = EvidenceBoundPaymentService(PaymentIdempotencyGuard(), CommercialEvidenceGate())
    result = s.verify("o1", "test-provider", None)
    assert result.verified is False
    assert result.reason == "PAYMENT_EVIDENCE_REQUIRED"


def test_mismatched_order_blocks_verification():
    gate = CommercialEvidenceGate()
    gate.add(ev("o2"))
    s = EvidenceBoundPaymentService(PaymentIdempotencyGuard(), gate)
    result = s.verify("o1", "test-provider", ev("o2"))
    assert result.verified is False
    assert result.reason == "EVIDENCE_ORDER_MISMATCH"


def test_matching_payment_evidence_allows_verification():
    gate = CommercialEvidenceGate()
    evidence = ev("o1")
    gate.add(evidence)
    s = EvidenceBoundPaymentService(PaymentIdempotencyGuard(), gate)
    result = s.verify("o1", "test-provider", evidence)
    assert result.verified is True
    assert result.reason == "PAYMENT_VERIFIED"
