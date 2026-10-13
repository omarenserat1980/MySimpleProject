import pytest

from brain_v12.business.crypto_mining_intelligence import PayoutEvidence
from brain_v12.business.crypto_mining_verification import BlockchainProof, VerificationState, start_cloud_mining_verification
from brain_v12.business.revenue_ledger import RevenueRecord


def _verified_cycle(opportunity_id: str) -> dict:
    cycle = start_cloud_mining_verification("CloudMineCrypto", opportunity_id)
    for state in (VerificationState.RISK_CHECK, VerificationState.FREE_TEST, VerificationState.MEASURE, VerificationState.WITHDRAWAL_TEST):
        cycle.advance(state, "test")
    cycle.submit_payout_evidence(PayoutEvidence(
        provider="CloudMineCrypto", observed_at="2026-10-02T23:30:00+03:00",
        balance_btc=0.0000012, withdrawal_requested_btc=0.000001, network="bitcoin",
        destination_fingerprint="wallet:sha256:abc", txid="tx-001",
        explorer_url="https://example.test/tx/tx-001", received_btc=0.00000095, fee_btc=0.00000005,
    ))
    return cycle.submit_blockchain_proof(BlockchainProof(
        txid="tx-001", explorer_url="https://example.test/tx/tx-001",
        confirmations=3, verified_at="2026-10-03T00:00:00+03:00",
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
    with pytest.raises(ValueError, match="verified payout evidence required"):
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
    with pytest.raises(ValueError, match="independent source required"):
        ledger.verify({"transaction_id": "tx-guard-002", "evidence_ref": "evidence://payment/tx-guard-002"})


def test_verified_payment_still_requires_delivery_reconciliation():
    ledger = RevenueRecord("commercial-guard-003", "100", "USD")
    ledger.verify({
        "transaction_id": "tx-guard-003",
        "evidence_ref": "evidence://payment/tx-guard-003",
        "source": "independent-bank-record",
        "verification_status": "INDEPENDENTLY_VERIFIED",
        "amount": "100",
        "currency": "USD",
    })
    with pytest.raises(ValueError, match="delivery_evidence_ref and reconciliation_ref"):
        ledger.realize({"delivery_evidence_ref": "evidence://delivery/guard-003"})


def test_repeated_verified_payment_is_idempotent():
    ledger = RevenueRecord("commercial-idempotent-001", "100", "USD")
    evidence = {
        "transaction_id": "tx-idempotent-001",
        "evidence_ref": "evidence://payment/tx-idempotent-001",
        "source": "independent-bank-record",
        "verification_status": "INDEPENDENTLY_VERIFIED",
        "amount": "100",
        "currency": "USD",
    }
    first = ledger.verify(evidence)
    second = ledger.verify(evidence)
    assert second == first
    assert len(second["evidence"]) == 1


def test_conflicting_payment_cannot_overwrite_verified_payment():
    ledger = RevenueRecord("commercial-idempotent-002", "100", "USD")
    first = {
        "transaction_id": "tx-original",
        "evidence_ref": "evidence://payment/tx-original",
        "source": "independent-bank-record",
        "verification_status": "INDEPENDENTLY_VERIFIED",
        "amount": "100",
        "currency": "USD",
    }
    ledger.verify(first)
    conflicting = {**first, "transaction_id": "tx-different", "evidence_ref": "evidence://payment/tx-different"}
    with pytest.raises(ValueError, match="conflicting payment evidence"):
        ledger.verify(conflicting)


def test_repeated_revenue_realization_is_idempotent():
    ledger = RevenueRecord("commercial-idempotent-003", "100", "USD")
    ledger.verify({
        "transaction_id": "tx-realize-003",
        "evidence_ref": "evidence://payment/tx-realize-003",
        "source": "independent-bank-record",
        "verification_status": "INDEPENDENTLY_VERIFIED",
        "amount": "100",
        "currency": "USD",
    })
    evidence = {
        "delivery_evidence_ref": "evidence://delivery/003",
        "reconciliation_ref": "evidence://reconciliation/003",
    }
    first = ledger.realize(evidence)
    second = ledger.realize(evidence)
    assert second == first
    assert len(second["evidence"]) == 2


def test_conflicting_revenue_realization_evidence_is_rejected():
    ledger = RevenueRecord("commercial-idempotent-004", "100", "USD")
    ledger.verify({
        "transaction_id": "tx-realize-004",
        "evidence_ref": "evidence://payment/tx-realize-004",
        "source": "independent-bank-record",
        "verification_status": "INDEPENDENTLY_VERIFIED",
        "amount": "100",
        "currency": "USD",
    })
    ledger.realize({
        "delivery_evidence_ref": "evidence://delivery/004",
        "reconciliation_ref": "evidence://reconciliation/004",
    })
    with pytest.raises(ValueError, match="conflicting realization evidence"):
        ledger.realize({
            "delivery_evidence_ref": "evidence://delivery/other",
            "reconciliation_ref": "evidence://reconciliation/other",
        })



def test_repeated_mining_realization_is_idempotent():
    result = _verified_cycle("cloudminecrypto-ledger-idempotent-005")
    ledger = RevenueRecord("cloudminecrypto-ledger-idempotent-005", "verified mining payout", "BTC")
    first = ledger.realize_from_mining_verification(result)
    second = ledger.realize_from_mining_verification(result)
    assert second == first
    assert len(second["evidence"]) == 1


def test_conflicting_mining_realization_evidence_is_rejected():
    result = _verified_cycle("cloudminecrypto-ledger-conflict-006")
    ledger = RevenueRecord("cloudminecrypto-ledger-conflict-006", "verified mining payout", "BTC")
    ledger.realize_from_mining_verification(result)
    conflicting = {**result, "provider": "DifferentProvider"}
    with pytest.raises(ValueError, match="conflicting mining evidence"):
        ledger.realize_from_mining_verification(conflicting)
