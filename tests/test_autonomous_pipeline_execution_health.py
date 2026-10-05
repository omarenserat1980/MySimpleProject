from platform_foundation.autonomous_pipeline import AutonomousPipeline
from platform_foundation.apm import APM
from platform_foundation.stage_orchestrator import StageOrchestrator
from platform_foundation.persistent_state import SQLiteStateStore


def make_pipeline(tmp_path, ci_executor=None):
    store = SQLiteStateStore(tmp_path / "state.db")
    return AutonomousPipeline(StageOrchestrator(store), APM(), ci_executor=ci_executor)


def test_pipeline_health_blocks_without_brain_ci_executor(tmp_path):
    pipeline = make_pipeline(tmp_path)
    health = pipeline.health()
    assert health["healthy"] is False
    assert health["status"] == "READY"
    assert "brain_ci_executor_unavailable" in health["issues"]


def test_pipeline_execution_health_requires_brain_executor(tmp_path):
    pipeline = make_pipeline(tmp_path)
    result = pipeline.execution_health()
    assert result["healthy"] is False
    assert result["status"] == "BLOCKED"
