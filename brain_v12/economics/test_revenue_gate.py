from economics.revenue_gate import PaymentEvidence, ConfirmedRevenue


def test_valid_evidence_can_create_revenue():
    e = PaymentEvidence(
        "ev-1", "opp-1", 25, "USD", "2026-10-08T01:00:00Z", "payment://verified/1"
    )
    r = ConfirmedRevenue.from_evidence(e)
    assert r.amount == 25
    assert r.evidence_id == "ev-1"


def test_missing_proof_cannot_create_revenue():
    e = PaymentEvidence(
        "ev-2", "opp-2", 25, "USD", "2026-10-08T01:00:00Z", ""
    )
    try:
        ConfirmedRevenue.from_evidence(e)
        assert False
    except ValueError:
        assert True
