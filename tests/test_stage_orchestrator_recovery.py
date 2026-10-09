from platform_foundation.stage_orchestrator import StageOrchestrator
from platform_foundation.persistent_state import SQLiteStateStore


def test_failed_stage_persists_resume_state(tmp_path):
    path = tmp_path / "state.db"
    store = SQLiteStateStore(str(path))
    orchestrator = StageOrchestrator(store)

    try:
        orchestrator.run_next(
            execute=lambda current: (_ for _ in ()).throw(RuntimeError("boom")),
            verify=lambda current, result: True,
            max_attempts=1,
        )
        assert False
    except RuntimeError:
        pass

    state = orchestrator.current()
    assert state.stage == 1
    assert state.status == "FAILED"
    assert state.attempts == 1
    assert "boom" in (state.last_error or "")
    store.close()


def test_retry_can_resume_same_stage(tmp_path):
    path = tmp_path / "state.db"
    store = SQLiteStateStore(str(path))
    orchestrator = StageOrchestrator(store)
    calls = {"n": 0}

    def execute(current):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transient")
        return True

    state = orchestrator.run_next(
        execute=execute,
        verify=lambda current, result: result is True,
        max_attempts=3,
    )

    assert state.stage == 2
    assert calls["n"] == 2
    store.close()
