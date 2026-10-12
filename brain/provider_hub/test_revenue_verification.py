from brain.provider_hub.evidence import CommercialEvidenceGate, Evidence
from brain.provider_hub.revenue_verification import RevenueVerificationService


def evidence(eid, etype, order="o1"):
    return Evidence(
        evidence_id=eid,
        evidence_type=etype,
        order_id=order,
        source="test",
        reference=eid,
        observed_at="2026-10-04T00:00:00Z",
        payload={"confirmed": True},
    )


def test_payment_alone_does_not_realize_revenue():
    gate = CommercialEvidenceGate()
    payment = evidence("p1", "PAYMENT_VERIFICATION")
    gate.add(payment)
    result = RevenueVerificationService(gate).verify("o1", payment, None)
    assert result.realized is False
    assert result.reason == "REVENUE_EVIDENCE_REQUIRED"


def test_both_evidence_types_are_required():
    gate = CommercialEvidenceGate()
    payment = evidence("p1", "PAYMENT_VERIFICATION")
    revenue = evidence("r1", "REVENUE_CONFIRMATION")
    gate.add(payment)
    gate.add(revenue)
    result = RevenueVerificationService(gate).verify("o1", payment, revenue)
    assert result.realized is True
    assert result.reason == "REVENUE_REALIZED"


def test_revenue_evidence_for_other_order_is_blocked():
    gate = CommercialEvidenceGate()
    payment = evidence("p1", "PAYMENT_VERIFICATION", "o1")
    revenue = evidence("r1", "REVENUE_CONFIRMATION", "o2")
    gate.add(payment)
    gate.add(revenue)
    result = RevenueVerificationService(gate).verify("o1", payment, revenue)
    assert result.realized is False
    assert result.reason == "REVENUE_ORDER_MISMATCH"
