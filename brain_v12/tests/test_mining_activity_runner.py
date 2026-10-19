from brain_v12.business.mining_activity_ledger import MiningActivityLedger
from brain_v12.brain.mining_activity_runner import run_and_record_pow_task


def test_actual_pow_task_result_is_persisted_without_payout_proof(tmp_path):
    db = tmp_path / "activity.sqlite"
    header = bytes(76) + bytes(4)
    with MiningActivityLedger(db) as ledger:
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


def test_cancelled_pow_task_is_also_recorded(tmp_path):
    with MiningActivityLedger(tmp_path / "activity.sqlite") as ledger:
        result, activity = run_and_record_pow_task(
            bytes(80), 1, activity_id="cancel-activity", run_id="cancel-run",
            ledger=ledger, cancel_requested=lambda: True,
        )
        assert result.status == "CANCELLED"
        assert result.hashes_checked == 0
        assert activity["payload"]["status"] == "CANCELLED"
        assert activity["income_status"] == "NO_REVENUE_CLAIM"
