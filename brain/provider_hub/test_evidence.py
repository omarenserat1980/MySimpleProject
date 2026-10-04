from brain.provider_hub.evidence import CommercialEvidenceGate, Evidence


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
