import pytest

from brain_v12.business.crypto_mining_intelligence import PayoutEvidence
from brain_v12.business.crypto_mining_verification import VerificationState, start_cloud_mining_verification
from brain_v12.business.revenue_ledger import RevenueRecord


def _verified_cycle(opportunity_id: str) -> dict:
    cycle = start_cloud_mining_verification("CloudMineCrypto", opportunity_id)
    for state in (VerificationState.RISK_CHECK, VerificationState.FREE_TEST, VerificationState.MEASURE, VerificationState.WITHDRAWAL_TEST):
        cycle.advance(state, "test")
    return cycle.submit_payout_evidence(PayoutEvidence(
        provider="CloudMineCrypto", observed_at="2026-10-02T23:30:00+03:00",
        balance_btc=0.0000012, withdrawal_requested_btc=0.000001, network="bitcoin",
        destination_fingerprint="wallet:sha256:abc", txid="tx-001",
        explorer_url="https://example.test/tx/tx-001", received_btc=0.00000095, fee_btc=0.00000005,
    ))


def test_mining_verification_is_the_gate_to_revenue_realized():
    result = _verified_cycle("cloudminecrypto-ledger-001")
    ledger = RevenueRecord("cloudminecrypto-ledger-001", "verified mining payout", "BTC")
    snapshot = ledger.realize_from_mining_verification(result)
    assert snapshot["status"] == "REVENUE_REALIZED"
    assert "tx-001" in snapshot["evidence"][0]


def test_unverified_mining_result_cannot_realize_revenue():
    cycle = start_cloud_mining_verification("CloudMineCrypto", "cloudminecrypto-ledger-002")
    ledger = RevenueRecord("cloudminecrypto-ledger-002", "unverified mining payout", "BTC")
    with pytest.raises(ValueError, match="REVENUE_REALIZED"):
        ledger.realize_from_mining_verification(cycle.snapshot())


def test_wrong_opportunity_cannot_realize_revenue():
    result = _verified_cycle("cloudminecrypto-ledger-003")
    ledger = RevenueRecord("different-opportunity", "verified mining payout", "BTC")
    with pytest.raises(ValueError, match="opportunity_id mismatch"):
        ledger.realize_from_mining_verification(result)


def test_free_form_payment_evidence_cannot_verify():
    ledger = RevenueRecord("commercial-guard-001", "payment", "USD")
    with pytest.raises(ValueError, match="structured payment evidence"):
        ledger.verify("payment evidence recorded")


def test_incomplete_structured_evidence_cannot_realize():
    ledger = RevenueRecord("commercial-guard-002", "payment", "USD")
    ledger.verify({"transaction_id": "tx-guard-002", "evidence_ref": "evidence://payment/tx-guard-002"})
    with pytest.raises(ValueError, match="delivery_evidence_ref"):
        ledger.realize({"delivery_evidence_ref": "evidence://delivery/guard-002"})
