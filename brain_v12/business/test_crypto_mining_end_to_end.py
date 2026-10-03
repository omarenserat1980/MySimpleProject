import pytest

from brain_v12.brain.cloud_mining_control_plane import CloudMiningControlPlane, CloudWorker
from brain_v12.business.crypto_mining_intelligence import PayoutEvidence
from brain_v12.business.crypto_mining_verification import (
    BlockchainProof,
    VerificationState,
    start_cloud_mining_verification,
)
from brain_v12.business.revenue_ledger import RevenueRecord


def test_worker_to_revenue_ledger_requires_every_gate():
    """Integration guard: worker evidence -> payout -> chain proof -> ledger."""
    cp = CloudMiningControlPlane()
    cp.register_worker(
        CloudWorker("worker-e2e-01", "vm", "user-region", "owner", enabled=True)
    )
    job = cp.plan("worker-e2e-01")

    admitted, reason = cp.admit(job.job_id, on_github_actions=False, temperature_c=40.0)
    assert admitted is True
    assert reason == "admitted_for_registered_worker"

    mining_evidence = cp.evidence(
        job.job_id, hashrate=1000.0, accepted=12, rejected=1, payout_tx_id="tx-e2e-001"
    )
    assert mining_evidence["status"] == "PAYOUT_TX_REFERENCE_PRESENT"

    cycle = start_cloud_mining_verification("CloudMineCrypto", job.job_id)
    for state in (
        VerificationState.RISK_CHECK,
        VerificationState.FREE_TEST,
        VerificationState.MEASURE,
        VerificationState.WITHDRAWAL_TEST,
    ):
        cycle.advance(state, "integration-test")

    payout = PayoutEvidence(
        provider="CloudMineCrypto",
        observed_at="2026-10-03T03:30:00Z",
        balance_btc=0.0000012,
        withdrawal_requested_btc=0.000001,
        network="bitcoin",
        destination_fingerprint="wallet:sha256:e2e",
        txid=mining_evidence["payout_tx_id"],
        explorer_url="https://example.test/tx/tx-e2e-001",
        received_btc=0.00000095,
        fee_btc=0.00000005,
    )
    payout_result = cycle.submit_payout_evidence(payout)
    assert payout_result["state"] == VerificationState.BLOCKCHAIN_VERIFY.value

    realized = cycle.submit_blockchain_proof(
        BlockchainProof(
            txid="tx-e2e-001",
            explorer_url="https://example.test/tx/tx-e2e-001",
            confirmations=3,
            verified_at="2026-10-03T03:31:00Z",
        )
    )
    assert realized["state"] == VerificationState.REVENUE_REALIZED.value
    assert realized["guardrails"]["brain_moves_funds"] is False

    ledger = RevenueRecord(job.job_id, "verified mining payout", "BTC")
    final = ledger.realize_from_mining_verification(realized)
    assert final["status"] == "REVENUE_REALIZED"
    assert any("tx-e2e-001" in item for item in final["evidence"])


def test_github_actions_worker_path_cannot_enter_the_integration_gate():
    cp = CloudMiningControlPlane()
    cp.register_worker(
        CloudWorker("worker-e2e-blocked", "vm", "user-region", "owner", enabled=True)
    )
    job = cp.plan("worker-e2e-blocked")
    admitted, reason = cp.admit(job.job_id, on_github_actions=True)
    assert admitted is False
    assert reason == "github_actions_mining_forbidden"
