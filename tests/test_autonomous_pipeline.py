from platform_foundation.apm import APM
from platform_foundation.autonomous_pipeline import AutonomousPipeline
from platform_foundation.persistent_state import SQLiteStateStore
from platform_foundation.stage_orchestrator import StageOrchestrator


def test_pipeline_instruments_verified_stage(tmp_path):
    store = SQLiteStateStore(tmp_path / "state.db")
    apm = APM(store, clock=lambda: 1.0)
    pipeline = AutonomousPipeline(StageOrchestrator(store), apm)
    result = pipeline.run_stage(
        execute=lambda state: {"stage": state.stage},
        verify=lambda state, result: result["stage"] == state.stage,
        task_id="task-1", run_id="run-1", commit_sha="abc",
    )
    assert result.stage_before == 1
    assert result.stage_after == 2
    assert result.verified is True
    assert pipeline.progress()["completed_stages"] == 1
    assert any(p["metric"] == "pipeline.stages.completed" for p in apm.snapshot())


def test_pipeline_does_not_advance_on_failed_verification(tmp_path):
    store = SQLiteStateStore(tmp_path / "state.db")
    apm = APM(store)
    pipeline = AutonomousPipeline(StageOrchestrator(store), apm)
    try:
        pipeline.run_stage(
            execute=lambda state: "bad",
            verify=lambda state, result: False,
            max_attempts=1,
        )
        assert False
    except RuntimeError:
        pass
    assert pipeline.progress()["stage"] == 1
    assert pipeline.progress()["status"] == "FAILED"


def test_pipeline_retries_and_records_retry_telemetry(tmp_path):
    store = SQLiteStateStore(tmp_path / "state.db")
    now = [0.0]
    apm = APM(store, clock=lambda: now[0])
    pipeline = AutonomousPipeline(StageOrchestrator(store), apm)
    calls = {"n": 0}

    def execute(state):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transient")
        return "ok"

    result = pipeline.run_stage(
        execute=execute, verify=lambda state, result: result == "ok", max_attempts=2
    )
    assert result.attempts == 2
    assert result.stage_after == 2
    assert any(
        p["metric"] == "operations.retries" and p["dimensions"]["operation"] == "stage.1.execute"
        for p in apm.snapshot()
    )
