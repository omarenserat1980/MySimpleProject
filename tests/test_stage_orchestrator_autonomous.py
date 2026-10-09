from platform_foundation.stage_orchestrator import StageOrchestrator
from platform_foundation.persistent_state import SQLiteStateStore


def test_run_next_requires_independent_verification(tmp_path):
    store = SQLiteStateStore(str(tmp_path / "state.db"))
    orchestrator = StageOrchestrator(store)

    try:
        orchestrator.run_next(execute=lambda state: "bad", verify=lambda state, result: False)
        assert False
    except RuntimeError:
        pass

    assert orchestrator.current().stage == 1
    store.close()


def test_run_next_advances_after_verification(tmp_path):
    store = SQLiteStateStore(str(tmp_path / "state.db"))
    orchestrator = StageOrchestrator(store)

    state = orchestrator.run_next(
        execute=lambda current: {"stage": current.stage, "verified": True},
        verify=lambda current, result: result["verified"] and result["stage"] == current.stage,
    )

    assert state.stage == 2
    assert state.status == "READY"
    store.close()
