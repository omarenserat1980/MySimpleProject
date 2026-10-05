from platform_foundation.apm import APM
from platform_foundation.autonomous_pipeline import AutonomousPipeline
from platform_foundation.persistent_state import SQLiteStateStore
from platform_foundation.stage_orchestrator import StageOrchestrator


def test_pipeline_persists_last_run(tmp_path):
    store = SQLiteStateStore(tmp_path / "state.db")
    p = AutonomousPipeline(StageOrchestrator(store), APM(store))
    run = p.run_until(
        execute=lambda s: s.stage,
        verify=lambda s, r: r == s.stage,
        stop_stage=3,
        run_id="run-16",
    )
    assert run.status == "READY"
    assert p.last_run() == run


def test_pipeline_failure_persists_failed_run(tmp_path):
    store = SQLiteStateStore(tmp_path / "state.db")
    p = AutonomousPipeline(StageOrchestrator(store), APM(store))
    try:
        p.run_until(
            execute=lambda s: s.stage,
            verify=lambda s, r: False,
            stop_stage=2,
            max_attempts=1,
            run_id="run-fail",
        )
    except RuntimeError:
        pass
    last = p.last_run()
    assert last is not None
    assert last.status == "FAILED"
    assert last.run_id == "run-fail"


def test_pipeline_progress_exposes_last_run(tmp_path):
    store = SQLiteStateStore(tmp_path / "state.db")
    p = AutonomousPipeline(StageOrchestrator(store), APM(store))
    p.run_until(execute=lambda s: s.stage, verify=lambda s, r: True, stop_stage=1)
    assert p.progress()["last_run"] is not None
