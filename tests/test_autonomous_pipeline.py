from platform_foundation.apm import APM
from platform_foundation.autonomous_pipeline import AutonomousPipeline
from platform_foundation.persistent_state import SQLiteStateStore
from platform_foundation.stage_orchestrator import StageOrchestrator


def test_verified_checkpoint_is_persisted_after_stage(tmp_path):
    store = SQLiteStateStore(tmp_path / "state.db")
    p = AutonomousPipeline(StageOrchestrator(store), APM(store))
    p.run_until(execute=lambda s: s.stage, verify=lambda s, r: r == s.stage, stop_stage=2, run_id="run-17")
    cp = p.checkpoint()
    assert cp is not None
    assert cp["stage"] == 3
    assert cp["status"] == "READY"
    assert cp["run_id"] == "run-17"


def test_failed_stage_does_not_create_new_verified_checkpoint(tmp_path):
    store = SQLiteStateStore(tmp_path / "state.db")
    p = AutonomousPipeline(StageOrchestrator(store), APM(store))
    p.run_until(execute=lambda s: s.stage, verify=lambda s, r: True, stop_stage=1)
    before = p.checkpoint()
    try:
        p.run_until(execute=lambda s: s.stage, verify=lambda s, r: False, stop_stage=2, max_attempts=1)
    except RuntimeError:
        pass
    assert p.checkpoint() == before
