from brain_v7.braincore_v2.fully_autonomous_runtime import AutonomousRuntime


def test_stop_file_blocks_cycle(tmp_path):
    stop = tmp_path / "STOP_BRAIN"
    stop.write_text("1")
    rt = AutonomousRuntime(
        state_path=str(tmp_path / "state.json"),
        stop_path=str(stop),
        sleep_seconds=1,
    )
    result = rt.run_cycle()
    assert result["status"] == "STOP_REQUESTED"


def test_runtime_persists_state(tmp_path):
    rt = AutonomousRuntime(
        state_path=str(tmp_path / "state.json"),
        stop_path=str(tmp_path / "STOP_BRAIN"),
        sleep_seconds=1,
    )
    assert rt.state.cycle == 0
    rt._save()
    assert (tmp_path / "state.json").exists()
