from brain_v12.business.crypto_mining_intelligence import PayoutEvidence
from brain_v12.business.crypto_mining_verification import (
    BlockchainProof, VerificationState, start_cloud_mining_verification,
)


def _ready_cycle(opportunity_id: str):
    cycle = start_cloud_mining_verification("CloudMineCrypto", opportunity_id)
    for state in (
        VerificationState.RISK_CHECK,
        VerificationState.FREE_TEST,
        VerificationState.MEASURE,
        VerificationState.WITHDRAWAL_TEST,
    ):
        cycle.advance(state, "test")
    return cycle


def _payout():
    return PayoutEvidence(
        provider="CloudMineCrypto",
        observed_at="2026-10-02T23:30:00+03:00",
        balance_btc=0.0000012,
        withdrawal_requested_btc=0.000001,
        network="bitcoin",
        destination_fingerprint="wallet:sha256:abc",
        txid="tx-001",
        explorer_url="https://example.test/tx/tx-001",
        received_btc=0.00000095,
        fee_btc=0.00000005,
    )


def test_cloud_mining_cycle_requires_explicit_blockchain_proof_before_realized():
    cycle = _ready_cycle("cloudminecrypto-free-001")

    result = cycle.submit_payout_evidence(_payout())

    assert result["state"] == VerificationState.BLOCKCHAIN_VERIFY.value
    assert result["history"][-1] == "BLOCKCHAIN_VERIFY"

    result = cycle.submit_blockchain_proof(BlockchainProof(
        txid="tx-001",
        explorer_url="https://example.test/tx/tx-001",
        confirmations=3,
        verified_at="2026-10-03T03:30:00Z",
    ))

    assert result["state"] == VerificationState.REVENUE_REALIZED.value
    assert result["history"][-2:] == ["BLOCKCHAIN_VERIFY", "REVENUE_REALIZED"]
    assert result["guardrails"]["payments_enabled"] is False


def test_mismatched_blockchain_proof_never_becomes_realized():
    cycle = _ready_cycle("cloudminecrypto-free-002")
    cycle.submit_payout_evidence(_payout())

    try:
        cycle.submit_blockchain_proof(BlockchainProof(
            txid="wrong-tx",
            explorer_url="https://example.test/tx/wrong-tx",
            confirmations=3,
            verified_at="2026-10-03T03:30:00Z",
        ))
    except ValueError as exc:
        assert "does not match" in str(exc)
    else:
        raise AssertionError("mismatched blockchain proof must be rejected")

    assert cycle.state == VerificationState.BLOCKCHAIN_VERIFY


def test_missing_chain_proof_never_becomes_realized():
    cycle = _ready_cycle("cloudminecrypto-free-003")

    result = cycle.submit_payout_evidence(PayoutEvidence(
        provider="CloudMineCrypto",
        observed_at="2026-10-02T23:30:00+03:00",
        balance_btc=0.0000012,
        withdrawal_requested_btc=0.000001,
        network="bitcoin",
        destination_fingerprint="wallet:sha256:abc",
    ))

    assert result["state"] == VerificationState.WITHDRAWAL_TEST.value
    assert result["evidence"]["payout_verification"]["financial_state"] == "EXPECTED"
