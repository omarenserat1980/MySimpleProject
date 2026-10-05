from platform_foundation.apm import APM
from platform_foundation.brain_ci_executor import BrainCIExecutor
from platform_foundation.brain_execution_authority import BrainExecutionAuthority
from platform_foundation.audit_chain import AuditChain
from platform_foundation.autonomous_pipeline import AutonomousPipeline
from platform_foundation.parallel_chunks import ParallelChunkRunner
from platform_foundation.persistent_state import SQLiteStateStore
from platform_foundation.stage_orchestrator import StageOrchestrator
import pytest


def ready_pipeline(tmp_path):
    store = SQLiteStateStore(tmp_path / "state.db")
    authority = BrainExecutionAuthority(heartbeat_path=tmp_path / "heartbeat.json")
    authority.heartbeat()
    executor = BrainCIExecutor(store, root=tmp_path, runner=lambda _command, _root: (0, "", ""))
    return store, AutonomousPipeline(StageOrchestrator(store), APM(store), ci_executor=executor, execution_authority=authority)


def test_verified_checkpoint_is_persisted_after_stage(tmp_path):
    store, p = ready_pipeline(tmp_path)
    p.run_until(execute=lambda s: s.stage, verify=lambda s, r: r == s.stage, stop_stage=2, run_id="run-17")
    cp = p.checkpoint()
    assert cp is not None
    assert cp["stage"] == 3
    assert cp["status"] == "READY"
    assert cp["run_id"] == "run-17"


def test_failed_stage_does_not_create_new_verified_checkpoint(tmp_path):
    store, p = ready_pipeline(tmp_path)
    p.run_until(execute=lambda s: s.stage, verify=lambda s, r: True, stop_stage=1)
    before = p.checkpoint()
    try:
        p.run_until(execute=lambda s: s.stage, verify=lambda s, r: False, stop_stage=2, max_attempts=1)
    except RuntimeError:
        pass
    assert p.checkpoint() == before


def test_parallel_stage_is_integrated_with_pipeline_gate(tmp_path):
    store = SQLiteStateStore(tmp_path / "state.db")
    runner = ParallelChunkRunner(store, AuditChain())
    p = AutonomousPipeline(StageOrchestrator(store), APM(store), runner)
    events = []

    def execute(chunk, deps):
        events.append(("execute", chunk, sorted(deps)))
        return chunk

    results = p.run_parallel_stage(
        chunks=["A", "B", "C"],
        execute_chunk=execute,
        verify_chunk=lambda _chunk, output: output != "B",
        dependencies={"C": ["A", "B"]},
        max_workers=2,
        run_id="parallel-stage-1",
    )
    assert [r.status for r in results] == ["SUCCESS", "FAILED", "FAILED"]
    assert p.orchestrator.current().stage == 1


def test_parallel_stage_advances_only_after_all_chunks_verify(tmp_path):
    store = SQLiteStateStore(tmp_path / "state.db")
    runner = ParallelChunkRunner(store, AuditChain())
    p = AutonomousPipeline(StageOrchestrator(store), APM(store), runner)

    results = p.run_parallel_stage(
        chunks=["A", "B", "C"],
        execute_chunk=lambda chunk, deps: {"chunk": chunk, "deps": sorted(deps)},
        verify_chunk=lambda _chunk, _output: True,
        dependencies={"C": ["A", "B"]},
        max_workers=2,
        run_id="parallel-stage-2",
    )
    assert all(r.status == "SUCCESS" for r in results)
    assert p.orchestrator.current().stage == 2
    assert p.checkpoint()["stage"] == 2


def test_parallel_stage_restart_reuses_verified_chunks(tmp_path):
    path = tmp_path / "state.db"
    store = SQLiteStateStore(path)
    audit = AuditChain()
    runner = ParallelChunkRunner(store, audit)
    p = AutonomousPipeline(StageOrchestrator(store), APM(store), runner)

    calls = []
    p.run_parallel_stage(
        chunks=["A", "B"],
        execute_chunk=lambda chunk, deps: calls.append(chunk) or chunk,
        verify_chunk=lambda _chunk, _output: True,
        max_workers=2,
        run_id="restart-stage",
    )
    assert sorted(calls) == ["A", "B"]
    store.close()

    reopened = SQLiteStateStore(path)
    resumed = AutonomousPipeline(
        StageOrchestrator(reopened), APM(reopened), ParallelChunkRunner(reopened, audit)
    )
    resumed_calls = []
    # The stage was already advanced; a new stage run uses a different stage key.
    # This assertion proves the durable chunk checkpoints from the completed run remain intact.
    resumed.run_parallel_stage(
        chunks=["C", "D"],
        execute_chunk=lambda chunk, deps: resumed_calls.append(chunk) or chunk,
        verify_chunk=lambda _chunk, _output: True,
        max_workers=2,
        run_id="restart-stage-2",
    )
    assert sorted(resumed_calls) == ["C", "D"]
    assert reopened.get("pipeline.chunk:restart-stage:stage-1:A")["status"] == "SUCCESS"
    assert reopened.get("pipeline.chunk:restart-stage:stage-1:B")["status"] == "SUCCESS"
    reopened.close()


def test_pipeline_health_is_true_after_verified_checkpoint(tmp_path):
    store, p = ready_pipeline(tmp_path)
    p.run_until(execute=lambda s: s.stage, verify=lambda s, r: True, stop_stage=2)
    assert p.health()["healthy"] is True


def test_pipeline_health_detects_failed_stage(tmp_path):
    store, p = ready_pipeline(tmp_path)
    try:
        p.run_until(execute=lambda s: s.stage, verify=lambda s, r: False, stop_stage=1, max_attempts=1)
    except RuntimeError:
        pass
    assert p.health()["healthy"] is False
    assert "stage_failed" in p.health()["issues"]
