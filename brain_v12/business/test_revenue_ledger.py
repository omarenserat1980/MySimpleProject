import pytest

from brain_v12.business.crypto_mining_intelligence import PayoutEvidence
from brain_v12.business.crypto_mining_verification import (
    BlockchainProof, VerificationState, start_cloud_mining_verification,
    _start_cloud_mining_verification_with_verifier,
)
from brain_v12.business.revenue_ledger import RevenueRecord


def _verified_cycle(opportunity_id: str) -> dict:
    # Test-only deterministic verifier; never evidence of a real chain transaction.
    cycle = _start_cloud_mining_verification_with_verifier(
        "CloudMineCrypto", opportunity_id,
        chain_verifier=lambda proof, payout: proof.txid == "tx-001",
    )
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


def _verified_payment_evidence(transaction_id="tx-idempotent-001"):
    return {
        "transaction_id": transaction_id,
        "evidence_ref": f"evidence://payment/{transaction_id}",
        "source": "independent-bank-record",
        "verification_status": "INDEPENDENTLY_VERIFIED",
        "amount": "100",
        "currency": "USD",
    }


def test_repeated_verified_payment_is_idempotent():
    ledger = RevenueRecord("commercial-idempotent-001", "100", "USD")
    evidence = _verified_payment_evidence()
    first = ledger.verify(evidence)
    second = ledger.verify(evidence)
    assert first == second
    assert len(ledger.evidence) == 1
    assert ledger.status == "PAYMENT_VERIFIED"


def test_conflicting_payment_evidence_is_rejected_after_verification():
    ledger = RevenueRecord("commercial-conflict-001", "100", "USD")
    ledger.verify(_verified_payment_evidence())
    with pytest.raises(ValueError, match="conflicting payment evidence"):
        ledger.verify(_verified_payment_evidence("tx-other"))


def test_repeated_realization_is_idempotent_and_snapshot_is_detached():
    ledger = RevenueRecord("commercial-realization-001", "100", "USD")
    ledger.verify(_verified_payment_evidence("tx-realization-001"))
    evidence = {
        "delivery_evidence_ref": "evidence://delivery/realization-001",
        "reconciliation_ref": "evidence://reconciliation/realization-001",
    }
    first = ledger.realize(evidence)
    second = ledger.realize(evidence)
    assert first == second
    assert len(ledger.evidence) == 2
    first["evidence"].append("caller-mutation")
    assert "caller-mutation" not in ledger.snapshot()["evidence"]


def test_conflicting_realization_evidence_is_rejected_after_realization():
    ledger = RevenueRecord("commercial-realization-conflict-001", "100", "USD")
    ledger.verify(_verified_payment_evidence("tx-realization-conflict-001"))
    ledger.realize({
        "delivery_evidence_ref": "evidence://delivery/original",
        "reconciliation_ref": "evidence://reconciliation/original",
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


def test_conflicting_mining_realization_is_rejected():
    result = _verified_cycle("cloudminecrypto-ledger-conflict-006")
    ledger = RevenueRecord("cloudminecrypto-ledger-conflict-006", "verified mining payout", "BTC")
    ledger.realize_from_mining_verification(result)
    conflicting = {**result, "provider": "DifferentProvider"}
    with pytest.raises(ValueError, match="conflicting mining evidence"):
        ledger.realize_from_mining_verification(conflicting)


def test_durable_store_survives_reopen_and_retries(tmp_path):
    from brain_v12.business.revenue_ledger_store import RevenueLedgerStore

    path = tmp_path / "revenue.db"
    payment = _verified_payment_evidence("durable-tx-001")
    delivery = {
        "delivery_evidence_ref": "evidence://delivery/durable-001",
        "reconciliation_ref": "evidence://reconciliation/durable-001",
    }
    store = RevenueLedgerStore(path)
    store.create("durable-opportunity-001", "100", "USD")
    first_payment = store.verify("durable-opportunity-001", payment)
    store = RevenueLedgerStore(path)
    assert store.get("durable-opportunity-001")["status"] == "PAYMENT_VERIFIED"
    assert store.verify("durable-opportunity-001", payment) == first_payment
    first_realization = store.realize("durable-opportunity-001", delivery)
    store = RevenueLedgerStore(path)
    assert store.realize("durable-opportunity-001", delivery) == first_realization
    assert store.get("durable-opportunity-001")["status"] == "REVENUE_REALIZED"
    assert len(store.get("durable-opportunity-001")["evidence"]) == 2


def test_durable_store_rolls_back_invalid_transition(tmp_path):
    from brain_v12.business.revenue_ledger_store import RevenueLedgerStore

    store = RevenueLedgerStore(tmp_path / "revenue.db")
    store.create("durable-rollback-001", "100", "USD")
    with pytest.raises(ValueError, match="independent source required"):
        store.verify("durable-rollback-001", {"transaction_id": "incomplete"})
    assert store.get("durable-rollback-001")["status"] == "PAYMENT_PENDING"
    assert store.get("durable-rollback-001")["evidence"] == []


def test_durable_store_rejects_conflicting_retry(tmp_path):
    from brain_v12.business.revenue_ledger_store import RevenueLedgerStore

    store = RevenueLedgerStore(tmp_path / "revenue.db")
    store.create("durable-conflict-001", "100", "USD")
    store.verify("durable-conflict-001", _verified_payment_evidence("original-tx"))
    with pytest.raises(ValueError, match="conflicting payment evidence"):
        store.verify("durable-conflict-001", _verified_payment_evidence("different-tx"))
    assert store.get("durable-conflict-001")["status"] == "PAYMENT_VERIFIED"
    with pytest.raises(ValueError, match="conflicting revenue record"):
        store.create("durable-conflict-001", "200", "USD")


def test_in_memory_store_supports_multiple_operations():
    from brain_v12.business.revenue_ledger_store import RevenueLedgerStore

    store = RevenueLedgerStore(":memory:")
    store.create("memory-opportunity-001", "100", "USD")
    assert store.get("memory-opportunity-001")["status"] == "PAYMENT_PENDING"
    assert store.verify("memory-opportunity-001", _verified_payment_evidence("memory-tx"))["status"] == "PAYMENT_VERIFIED"
    store.close()


def test_concurrent_identical_payment_retries_are_serialized(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from brain_v12.business.revenue_ledger_store import RevenueLedgerStore

    path = tmp_path / "concurrent-revenue.db"
    RevenueLedgerStore(path).create("concurrent-opportunity-001", "100", "USD")
    evidence = _verified_payment_evidence("concurrent-tx-001")

    def verify_once(_):
        return RevenueLedgerStore(path).verify("concurrent-opportunity-001", evidence)

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(verify_once, range(12)))

    assert all(result == results[0] for result in results)
    assert results[0]["status"] == "PAYMENT_VERIFIED"
    assert len(results[0]["evidence"]) == 1
