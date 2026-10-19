import pytest

from brain_v12.business.mining_activity_ledger import MiningActivityLedger


def test_activity_is_recorded_without_payout_proof_and_is_not_revenue():
    ledger = MiningActivityLedger(":memory:")
    item = ledger.record(
        activity_id="activity-1",
        run_id="run-1",
        mode="SIMULATION",
        activity_type="SHA256D_RESULT",
        payload={"hashes_tested": 1000, "valid_vectors": 1000},
    )
    assert item["activity_status"] == "SIMULATION_RECORDED"
    assert item["income_status"] == "NO_REVENUE_CLAIM"
    assert item["counts_as_verified_revenue"] is False
    assert ledger.get("activity-1") == item
    ledger.close()


def test_estimated_revenue_is_separate_from_verified_revenue():
    ledger = MiningActivityLedger(":memory:")
    item = ledger.record(
        activity_id="activity-2",
        run_id="run-2",
        mode="LIVE",
        activity_type="HASHRATE_MEASUREMENT",
        source="authorized-worker-telemetry",
        payload={"hashrate_hs": 1234},
        estimated_amount="0.000001",
        estimated_currency="BTC",
    )
    assert item["activity_status"] == "LIVE_ACTIVITY_UNVERIFIED"
    assert item["income_status"] == "ESTIMATE_ONLY"
    assert item["estimated_amount"] == "0.000001"
    assert item["counts_as_verified_revenue"] is False
    ledger.close()


def test_missing_source_does_not_discard_observation():
    ledger = MiningActivityLedger(":memory:")
    item = ledger.record(
        activity_id="activity-3",
        run_id="run-3",
        mode="LIVE",
        activity_type="ACCEPTED_SHARES",
        payload={"accepted_interval": 0},
    )
    assert item["activity_status"] == "SOURCE_MISSING"
    assert ledger.get("activity-3") is not None
    ledger.close()


def test_exact_retry_is_idempotent_but_conflicting_retry_is_rejected():
    ledger = MiningActivityLedger(":memory:")
    args = dict(
        activity_id="activity-4", run_id="run-4", mode="SIMULATION",
        activity_type="SIMULATOR_RUN", observed_at="2026-10-19T10:00:00Z",
        payload={"cycles": 5},
    )
    first = ledger.record(**args)
    assert ledger.record(**args) == first
    with pytest.raises(ValueError, match="conflicting activity_id"):
        ledger.record(**{**args, "payload": {"cycles": 6}})
    ledger.close()


@pytest.mark.parametrize("amount", ["-1", "NaN", "Infinity", "not-a-number"])
def test_invalid_estimate_is_rejected(amount):
    ledger = MiningActivityLedger(":memory:")
    with pytest.raises(ValueError, match="finite non-negative"):
        ledger.record(
            activity_id="activity-invalid", run_id="run-invalid",
            mode="SIMULATION", activity_type="SIMULATOR_RUN",
            payload={}, estimated_amount=amount, estimated_currency="BTC",
        )
    ledger.close()


def test_estimate_requires_currency_and_currency_requires_amount():
    ledger = MiningActivityLedger(":memory:")
    base = dict(
        activity_id="activity-5", run_id="run-5", mode="SIMULATION",
        activity_type="SIMULATOR_RUN", payload={},
    )
    with pytest.raises(ValueError, match="estimated_currency"):
        ledger.record(**{**base, "estimated_amount": "1"})
    with pytest.raises(ValueError, match="estimated_amount"):
        ledger.record(**{**base, "estimated_currency": "BTC"})
    ledger.close()


def test_invalid_mode_and_payload_fail_clearly():
    ledger = MiningActivityLedger(":memory:")
    base = dict(
        activity_id="activity-6", run_id="run-6",
        activity_type="SIMULATOR_RUN", payload={},
    )
    with pytest.raises(ValueError, match="mode must be"):
        ledger.record(**{**base, "mode": "MAGIC"})
    with pytest.raises(ValueError, match="payload must"):
        ledger.record(**{**base, "mode": "SIMULATION", "payload": "not-object"})
    ledger.close()



def test_generated_timestamp_retry_is_idempotent():
    ledger = MiningActivityLedger(":memory:")
    args = dict(
        activity_id="activity-generated-time", run_id="run-time",
        mode="SIMULATION", activity_type="SIMULATOR_RUN", payload={"cycles": 7},
    )
    first = ledger.record(**args)
    second = ledger.record(**args)
    assert second == first
    ledger.close()


def test_activity_survives_database_reopen(tmp_path):
    path = tmp_path / "mining-activity.db"
    ledger = MiningActivityLedger(path)
    saved = ledger.record(
        activity_id="activity-durable", run_id="run-durable",
        mode="SIMULATION", activity_type="SHA256D_RESULT",
        payload={"vectors_checked": 42},
    )
    ledger.close()

    reopened = MiningActivityLedger(path)
    assert reopened.get("activity-durable") == saved
    reopened.close()
