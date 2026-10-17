from brain.provider_hub.evidence import CommercialEvidenceGate, Evidence
from brain.provider_hub.payment_guard import PaymentIdempotencyGuard
from brain.provider_hub.payment_verification import EvidenceBoundPaymentService


def ev(order="o1", *, source="test-provider", evidence_type="PAYMENT_VERIFICATION"):
    return Evidence(
        evidence_id="pay-1",
        evidence_type=evidence_type,
        order_id=order,
        source=source,
        reference="txn-123",
        observed_at="2026-10-04T00:00:00Z",
        payload={"status": "paid"},
    )


def service(gate, verifier=None):
    return EvidenceBoundPaymentService(
        PaymentIdempotencyGuard(), gate, provider_evidence_verifier=verifier
    )


def trusted_verifier(evidence, provider_id):
    return provider_id == "test-provider" and evidence.payload.get("status") == "paid"


def test_missing_evidence_blocks_verification():
    result = service(CommercialEvidenceGate(), trusted_verifier).verify(
        "o1", "test-provider", None
    )
    assert result.verified is False
    assert result.reason == "PAYMENT_EVIDENCE_REQUIRED"


def test_mismatched_order_blocks_verification():
    gate = CommercialEvidenceGate()
    gate.add(ev("o2"))
    result = service(gate, trusted_verifier).verify("o1", "test-provider", ev("o2"))
    assert result.verified is False
    assert result.reason == "EVIDENCE_ORDER_MISMATCH"


def test_recorded_evidence_requires_trusted_provider_verifier():
    gate = CommercialEvidenceGate()
    evidence = ev()
    gate.add(evidence)
    result = service(gate).verify("o1", "test-provider", evidence)
    assert result.verified is False
    assert result.reason == "TRUSTED_PROVIDER_VERIFIER_NOT_CONFIGURED"


def test_matching_registered_evidence_and_trusted_verifier_allows_verification():
    gate = CommercialEvidenceGate()
    evidence = ev("o1")
    gate.add(evidence)
    result = service(gate, trusted_verifier).verify("o1", "test-provider", evidence)
    assert result.verified is True
    assert result.reason == "PAYMENT_VERIFIED"


def test_unregistered_evidence_cannot_reuse_another_payment_record():
    gate = CommercialEvidenceGate()
    gate.add(ev("o1"))
    unregistered = Evidence(
        evidence_id="attacker-row",
        evidence_type="PAYMENT_VERIFICATION",
        order_id="o1",
        source="test-provider",
        reference="different-transaction",
        observed_at="2026-10-04T00:00:00Z",
        payload={"status": "paid"},
    )
    result = service(gate, trusted_verifier).verify("o1", "test-provider", unregistered)
    assert result.verified is False
    assert result.reason == "PAYMENT_EVIDENCE_NOT_REGISTERED"


def test_wrong_provider_blocks_verification():
    gate = CommercialEvidenceGate()
    evidence = ev(source="other-provider")
    gate.add(evidence)
    result = service(gate, trusted_verifier).verify("o1", "test-provider", evidence)
    assert result.verified is False
    assert result.reason == "EVIDENCE_PROVIDER_MISMATCH"


def test_wrong_evidence_type_blocks_verification():
    gate = CommercialEvidenceGate()
    evidence = ev(evidence_type="REVENUE_CONFIRMATION")
    gate.add(evidence)
    result = service(gate, trusted_verifier).verify("o1", "test-provider", evidence)
    assert result.verified is False
    assert result.reason == "PAYMENT_VERIFICATION_EVIDENCE_TYPE_REQUIRED"


def test_verifier_exception_fails_closed():
    gate = CommercialEvidenceGate()
    evidence = ev()
    gate.add(evidence)

    def broken_verifier(evidence, provider_id):
        raise RuntimeError("provider unavailable")

    result = service(gate, broken_verifier).verify("o1", "test-provider", evidence)
    assert result.verified is False
    assert result.reason == "TRUSTED_PROVIDER_EVIDENCE_REJECTED"
