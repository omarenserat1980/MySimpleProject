from brain_v12.business.crypto_mining_intelligence import PayoutEvidence
from brain_v12.business.crypto_mining_verification import (
    VerificationState, start_cloud_mining_verification,
)


def test_cloud_mining_cycle_reaches_realized_only_with_payout_and_chain_evidence():
    cycle = start_cloud_mining_verification("CloudMineCrypto", "cloudminecrypto-free-001")
    cycle.advance(VerificationState.RISK_CHECK, "provider terms reviewed")
    cycle.advance(VerificationState.FREE_TEST, "no-pay gate")
    cycle.advance(VerificationState.MEASURE, "free plan metrics captured")
    cycle.advance(VerificationState.WITHDRAWAL_TEST, "withdrawal threshold reached")

    result = cycle.submit_payout_evidence(PayoutEvidence(
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
    ))

    assert result["state"] == VerificationState.REVENUE_REALIZED.value
    assert result["history"][-2:] == ["BLOCKCHAIN_VERIFY", "REVENUE_REALIZED"]
    assert result["guardrails"]["payments_enabled"] is False


def test_missing_chain_proof_never_becomes_realized():
    cycle = start_cloud_mining_verification("CloudMineCrypto", "cloudminecrypto-free-002")
    for state in (
        VerificationState.RISK_CHECK,
        VerificationState.FREE_TEST,
        VerificationState.MEASURE,
        VerificationState.WITHDRAWAL_TEST,
    ):
        cycle.advance(state, "test")

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
