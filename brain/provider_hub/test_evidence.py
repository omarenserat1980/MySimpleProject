from brain.provider_hub.evidence import CommercialEvidenceGate, Evidence
from brain.provider_hub.payment_guard import PaymentIdempotencyGuard
from brain.provider_hub.payment_verification import EvidenceBoundPaymentService


def ev(eid, typ, oid, ref):
    return Evidence.create(eid, typ, oid, "test", ref, {"ok": True})


def test_payment_gate():
    g = CommercialEvidenceGate()
    g.add(ev("e1", "PAYMENT_VERIFICATION", "o1", "pay-1"))
    assert g.can_mark_payment_verified("o1") is True


def test_revenue_requires_payment_and_confirmation():
    g = CommercialEvidenceGate()
    g.add(ev("e1", "PAYMENT_VERIFICATION", "o1", "pay-1"))
    assert g.can_mark_revenue_realized("o1") is False
    g.add(ev("e2", "REVENUE_CONFIRMATION", "o1", "ledger-1"))
    assert g.can_mark_revenue_realized("o1") is True


def test_delivery_requires_delivery_evidence():
    g = CommercialEvidenceGate()
    assert g.can_mark_delivery_verified("o1") is False
    g.add(ev("e3", "DELIVERY_VERIFICATION", "o1", "artifact-1"))
    assert g.can_mark_delivery_verified("o1") is True


def test_duplicate_evidence_rejected():
    g = CommercialEvidenceGate()
    g.add(ev("e1", "PAYMENT_VERIFICATION", "o1", "pay-1"))
    try:
        g.add(ev("e1", "PAYMENT_VERIFICATION", "o1", "pay-2"))
    except ValueError as e:
        assert str(e) == "DUPLICATE_EVIDENCE:e1"
    else:
        raise AssertionError("duplicate evidence accepted")


def _payment_service(verifier=None):
    return EvidenceBoundPaymentService(
        PaymentIdempotencyGuard(), CommercialEvidenceGate(), verifier
    )


def test_payment_verification_fails_closed_without_provider_verifier():
    service = _payment_service()
    evidence = ev("pay-e1", "PAYMENT_VERIFICATION", "order-1", "tx-1")
    service.evidence.add(evidence)

    result = service.verify("order-1", "test", evidence)

    assert result.verified is False
    assert result.reason == "TRUSTED_PROVIDER_VERIFIER_NOT_CONFIGURED"


def test_payment_verification_requires_registered_evidence():
    service = _payment_service(lambda evidence, provider: True)
    evidence = ev("pay-e2", "PAYMENT_VERIFICATION", "order-1", "tx-2")

    result = service.verify("order-1", "test", evidence)

    assert result.verified is False
    assert result.reason == "PAYMENT_EVIDENCE_NOT_REGISTERED"


def test_payment_verification_rejects_provider_mismatch():
    service = _payment_service(lambda evidence, provider: True)
    evidence = Evidence.create(
        "pay-e3", "PAYMENT_VERIFICATION", "order-1", "different-provider",
        "tx-3", {"ok": True}
    )
    service.evidence.add(evidence)

    result = service.verify("order-1", "test", evidence)

    assert result.verified is False
    assert result.reason == "EVIDENCE_PROVIDER_MISMATCH"


def test_payment_verification_rejects_false_or_non_boolean_verifier_results():
    for verifier_result in (False, 1, "true", None):
        service = _payment_service(
            lambda evidence, provider, value=verifier_result: value
        )
        evidence = ev(
            f"pay-e4-{verifier_result!s}", "PAYMENT_VERIFICATION",
            "order-1", "tx-4"
        )
        service.evidence.add(evidence)

        result = service.verify("order-1", "test", evidence)

        assert result.verified is False
        assert result.reason == "TRUSTED_PROVIDER_EVIDENCE_REJECTED"


def test_payment_verification_succeeds_only_after_trusted_verifier_accepts():
    service = _payment_service(
        lambda evidence, provider: (
            evidence.reference == "tx-5" and provider == "test"
        )
    )
    evidence = ev("pay-e5", "PAYMENT_VERIFICATION", "order-1", "tx-5")
    service.evidence.add(evidence)

    result = service.verify("order-1", "test", evidence)

    assert result.verified is True
    assert result.reason == "PAYMENT_VERIFIED"
    assert result.evidence_id == "pay-e5"


def test_payment_verification_treats_verifier_exception_as_rejection():
    def broken_verifier(evidence, provider):
        raise RuntimeError("provider verifier unavailable")

    service = _payment_service(broken_verifier)
    evidence = ev("pay-e6", "PAYMENT_VERIFICATION", "order-1", "tx-6")
    service.evidence.add(evidence)

    result = service.verify("order-1", "test", evidence)

    assert result.verified is False
    assert result.reason == "TRUSTED_PROVIDER_EVIDENCE_REJECTED"
