from platform_foundation.stage_orchestrator import StageOrchestrator
from platform_foundation.persistent_state import SQLiteStateStore


def test_stage_progress_is_durable(tmp_path):
    path = tmp_path / "state.db"
    first = SQLiteStateStore(str(path))
    state1 = StageOrchestrator(first).advance(stage=2, step=4, gate_passed=True)
    first.close()
    second = SQLiteStateStore(str(path))
    state2 = StageOrchestrator(second).current()
    second.close()
    assert state2 == state1


def test_stage_cannot_advance_without_gate(tmp_path):
    store = SQLiteStateStore(str(tmp_path / "state.db"))
    orchestrator = StageOrchestrator(store)
    try:
        orchestrator.advance(stage=2, step=1, gate_passed=False)
        assert False
    except RuntimeError:
        pass
    store.close()


def test_stage_regression_is_forbidden(tmp_path):
    store = SQLiteStateStore(str(tmp_path / "state.db"))
    orchestrator = StageOrchestrator(store)
    orchestrator.advance(stage=2, step=1, gate_passed=True)
    try:
        orchestrator.advance(stage=1, step=1, gate_passed=True)
        assert False
    except RuntimeError:
        pass
    store.close()


def test_stage_skipping_is_forbidden(tmp_path):
    store = SQLiteStateStore(str(tmp_path / "state.db"))
    orchestrator = StageOrchestrator(store)
    try:
        orchestrator.advance(stage=3, step=1, gate_passed=True)
        assert False
    except RuntimeError:
        pass
    store.close()


def test_final_stage_is_marked_complete(tmp_path):
    store = SQLiteStateStore(str(tmp_path / "state.db"))
    orchestrator = StageOrchestrator(store)
    state = None
    for stage in range(1, 42):
        state = orchestrator.advance(stage=stage, step=1, gate_passed=True)
    store.close()
    assert state is not None
    assert state.stage == 41
    assert state.status == "COMPLETE"
