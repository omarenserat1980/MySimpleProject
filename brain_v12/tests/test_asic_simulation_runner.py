from brain_v12.business.mining_activity_ledger import MiningActivityLedger
from brain_v12.brain.asic_simulation_runner import run_and_record_asic_simulation


def test_asic_logic_simulator_run_is_persisted_as_simulation_only(tmp_path):
    ledger = MiningActivityLedger(tmp_path / "activity.sqlite")
    try:
        report, activity = run_and_record_asic_simulation(
            {
                "nodes": [
                    {"name": "a", "op": "INPUT"},
                    {"name": "b", "op": "INPUT"},
                    {"name": "y", "op": "AND", "inputs": ["a", "b"]},
                ],
                "outputs": ["y"],
            },
            [{"a": 1, "b": 1}],
            activity_id="asic-sim-activity-1",
            run_id="asic-sim-run-1",
            ledger=ledger,
        )
        assert report["ok"] is True
        assert report["summary"]["real_hardware_measurement"] is False
        assert activity["activity_type"] == "SIMULATOR_RUN"
        assert activity["payload"]["model"] == "IDEAL_2_STATE_DIGITAL"
        assert activity["income_status"] == "NO_REVENUE_CLAIM"
        assert activity["counts_as_verified_revenue"] is False
        assert ledger.get("asic-sim-activity-1") is not None
    finally:
        ledger.close()


def test_invalid_asic_simulation_does_not_record_success(tmp_path):
    ledger = MiningActivityLedger(tmp_path / "activity.sqlite")
    try:
        try:
            run_and_record_asic_simulation(
                {"nodes": []}, [{"a": 1}],
                activity_id="bad-sim", run_id="bad-sim-run", ledger=ledger,
            )
        except ValueError:
            pass
        else:
            raise AssertionError("invalid netlist should fail")
        assert ledger.get("bad-sim") is None
    finally:
        ledger.close()
