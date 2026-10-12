from brain.provider_hub.delivery_verification import DeliveryVerificationService
from brain.provider_hub.evidence import CommercialEvidenceGate, Evidence


def ev(order="o1"):
    return Evidence(
        evidence_id="d1",
        evidence_type="DELIVERY_VERIFICATION",
        order_id=order,
        source="test-delivery",
        reference="delivery-123",
        observed_at="2026-10-04T00:00:00Z",
        payload={"delivered": True},
    )


def test_missing_delivery_evidence_blocks():
    gate = CommercialEvidenceGate()
    result = DeliveryVerificationService(gate).verify("o1", None)
    assert result.verified is False
    assert result.reason == "DELIVERY_EVIDENCE_REQUIRED"


def test_wrong_order_blocks_delivery():
    gate = CommercialEvidenceGate()
    evidence = ev("o2")
    gate.add(evidence)
    result = DeliveryVerificationService(gate).verify("o1", evidence)
    assert result.verified is False
    assert result.reason == "DELIVERY_ORDER_MISMATCH"


def test_delivery_evidence_allows_verification():
    gate = CommercialEvidenceGate()
    evidence = ev()
    gate.add(evidence)
    result = DeliveryVerificationService(gate).verify("o1", evidence)
    assert result.verified is True
    assert result.reason == "DELIVERY_VERIFIED"
