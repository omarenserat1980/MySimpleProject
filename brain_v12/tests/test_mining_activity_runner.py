from brain_v12.business.mining_activity_ledger import MiningActivityLedger
from brain_v12.brain.mining_activity_runner import run_and_record_pow_task


def test_actual_pow_task_result_is_persisted_without_payout_proof(tmp_path):
    db = tmp_path / "activity.sqlite"
    header = bytes(76) + bytes(4)
    ledger = MiningActivityLedger(db)
    try:
        result, activity = run_and_record_pow_task(
            header, (1 << 256) - 1,
            activity_id="pow-run-activity-1", run_id="pow-run-1",
            ledger=ledger, max_total_hashes=4, batch_hashes=2,
        )
        assert result.hashes_checked == 1
        assert activity["payload"]["status"] == "NONCE_FOUND_UNSUBMITTED"
        assert activity["payload"]["pool_contacted"] is False
        assert activity["activity_status"] == "SIMULATION_RECORDED"
        assert activity["income_status"] == "NO_REVENUE_CLAIM"
        assert activity["counts_as_verified_revenue"] is False
        persisted = ledger.get("pow-run-activity-1")
        assert persisted["payload"]["hashes_checked"] == 1
        assert persisted["counts_as_verified_revenue"] is False
    finally:
        ledger.close()


def test_cancelled_pow_task_is_also_recorded(tmp_path):
    ledger = MiningActivityLedger(tmp_path / "activity.sqlite")
    try:
        result, activity = run_and_record_pow_task(
            bytes(80), 1, activity_id="cancel-activity", run_id="cancel-run",
            ledger=ledger, cancel_requested=lambda: True,
        )
        assert result.status == "CANCELLED"
        assert result.hashes_checked == 0
        assert activity["payload"]["status"] == "CANCELLED"
        assert activity["income_status"] == "NO_REVENUE_CLAIM"
    finally:
        ledger.close()


def test_cpu_sha256d_benchmark_records_rate_as_unverified_activity(tmp_path):
    from brain_v12.brain.mining_activity_runner import benchmark_and_record_cpu_sha256d

    ledger = MiningActivityLedger(tmp_path / "activity.sqlite")
    try:
        measurement, activity = benchmark_and_record_cpu_sha256d(
            activity_id="cpu-bench-activity",
            run_id="cpu-bench-run",
            ledger=ledger,
            header_prefix=bytes(76),
            hashes_per_sample=8,
            repeats=2,
        )
        assert measurement["execution"] == "host_cpu_software"
        assert measurement["hashes_per_sample"] == 8
        assert measurement["median_hashes_per_second"] > 0
        assert measurement["is_live_mining"] is False
        assert measurement["is_rtl_or_asic_measurement"] is False
        assert activity["activity_type"] == "HASHRATE_MEASUREMENT"
        assert activity["income_status"] == "NO_REVENUE_CLAIM"
        assert activity["counts_as_verified_revenue"] is False
        assert ledger.get("cpu-bench-activity") is not None
    finally:
        ledger.close()


def test_cpu_sha256d_benchmark_rejects_unbounded_inputs(tmp_path):
    from brain_v12.brain.mining_activity_runner import benchmark_and_record_cpu_sha256d

    ledger = MiningActivityLedger(tmp_path / "activity.sqlite")
    try:
        try:
            benchmark_and_record_cpu_sha256d(
                activity_id="bad-bench", run_id="bad-bench-run",
                ledger=ledger, header_prefix=bytes(76),
                hashes_per_sample=1_000_001,
            )
        except ValueError as exc:
            assert "HASHES_PER_SAMPLE_OUT_OF_RANGE" in str(exc)
        else:
            raise AssertionError("oversized benchmark should be rejected")
        assert ledger.get("bad-bench") is None
    finally:
        ledger.close()
