import pytest

from brain_v12.business.pipeline import Opportunity


def make_opp():
    return Opportunity("OPP-PIPE-001", "Example", "problem", "offer")


def test_payment_verification_requires_structured_evidence():
    opp = make_opp()
    opp.transition("PAYMENT_PENDING", "evidence://payment/pending")
    with pytest.raises(ValueError, match="structured payment evidence"):
        opp.transition("PAYMENT_VERIFIED", "payment received")
    assert opp.stage == "PAYMENT_PENDING"


def test_payment_verification_requires_transaction_and_evidence_ref():
    opp = make_opp()
    opp.transition("PAYMENT_PENDING", "evidence://payment/pending")
    with pytest.raises(ValueError, match="transaction_id and evidence_ref"):
        opp.transition("PAYMENT_VERIFIED", {"transaction_id": "tx-only"})
    assert opp.stage == "PAYMENT_PENDING"


def test_revenue_realization_requires_verified_payment():
    opp = make_opp()
    with pytest.raises(ValueError, match="payment must be verified"):
        opp.transition("REVENUE_REALIZED", {
            "delivery_evidence_ref": "evidence://delivery/1",
            "reconciliation_ref": "evidence://reconciliation/1",
        })


def test_revenue_realization_requires_delivery_and_reconciliation():
    opp = make_opp()
    opp.transition("PAYMENT_PENDING", "evidence://payment/pending")
    opp.transition("PAYMENT_VERIFIED", {
        "transaction_id": "tx-1",
        "evidence_ref": "evidence://payment/tx-1",
    })
    with pytest.raises(ValueError, match="delivery_evidence_ref and reconciliation_ref"):
        opp.transition("REVENUE_REALIZED", {
            "delivery_evidence_ref": "evidence://delivery/1",
        })
    assert opp.stage == "PAYMENT_VERIFIED"


def test_full_financial_chain_reaches_realized():
    opp = make_opp()
    opp.transition("PAYMENT_PENDING", "evidence://payment/pending")
    opp.transition("PAYMENT_VERIFIED", {
        "transaction_id": "tx-1",
        "evidence_ref": "evidence://payment/tx-1",
    })
    result = opp.transition("REVENUE_REALIZED", {
        "delivery_evidence_ref": "evidence://delivery/1",
        "reconciliation_ref": "evidence://reconciliation/tx-1",
    })
    assert result["stage"] == "REVENUE_REALIZED"
