from platform_foundation.apm import APM
from platform_foundation.autonomous_pipeline import AutonomousPipeline
from platform_foundation.persistent_state import SQLiteStateStore
from platform_foundation.stage_orchestrator import StageOrchestrator


def test_pipeline_runs_multiple_stages_from_checkpoint(tmp_path):
    store = SQLiteStateStore(tmp_path / "state.db")
    pipeline = AutonomousPipeline(StageOrchestrator(store), APM(store))
    seen = []
    run = pipeline.run_until(
        execute=lambda state: seen.append(state.stage) or state.stage,
        verify=lambda state, result: result == state.stage,
        stop_stage=4,
    )
    assert run.status == "READY"
    assert run.stages_completed == 4
    assert seen == [1, 2, 3, 4]
    assert pipeline.progress()["stage"] == 5


def test_pipeline_stops_at_failed_gate_and_preserves_checkpoint(tmp_path):
    store = SQLiteStateStore(tmp_path / "state.db")
    pipeline = AutonomousPipeline(StageOrchestrator(store), APM(store))
    calls = []
    def verify(state, result):
        return state.stage != 3
    try:
        pipeline.run_until(
            execute=lambda state: calls.append(state.stage) or state.stage,
            verify=verify, stop_stage=5, max_attempts=1,
        )
        assert False
    except RuntimeError:
        pass
    assert calls == [1, 2, 3]
    assert pipeline.progress()["stage"] == 3
    assert pipeline.progress()["status"] == "FAILED"


def test_pipeline_resumes_after_checkpoint(tmp_path):
    store = SQLiteStateStore(tmp_path / "state.db")
    pipeline = AutonomousPipeline(StageOrchestrator(store), APM(store))
    calls = []
    try:
        pipeline.run_until(
            execute=lambda state: calls.append(state.stage) or state.stage,
            verify=lambda state, result: state.stage < 3,
            stop_stage=4, max_attempts=1,
        )
    except RuntimeError:
        pass
    calls.clear()
    run = pipeline.run_until(
        execute=lambda state: calls.append(state.stage) or state.stage,
        verify=lambda state, result: True,
        stop_stage=4,
    )
    assert run.stages_completed == 2
    assert calls == [3, 4]
