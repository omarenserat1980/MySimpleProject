from platform_foundation.persistent_state import SQLiteStateStore
from platform_foundation.task_orchestrator import TaskOrchestrator
from platform_foundation.task_state import InvalidTaskTransition, TaskStatus


def test_task_lifecycle_is_durable(tmp_path):
    path = tmp_path / "state.db"
    store = SQLiteStateStore(path)
    tasks = TaskOrchestrator(store)

    assert tasks.current("t1").status is TaskStatus.PENDING
    tasks.start("t1")
    failed = tasks.fail("t1", "temporary")
    assert failed.status is TaskStatus.FAILED
    retrying = tasks.retry("t1", "retrying")
    assert retrying.status is TaskStatus.RETRYING
    assert retrying.attempts == 1
    running = tasks.start("t1")
    assert running.status is TaskStatus.RUNNING
    done = tasks.succeed("t1", {"verified": True})
    assert done.status is TaskStatus.SUCCESS
    assert TaskOrchestrator(store).current("t1").output == {"verified": True}
    store.close()


def test_terminal_tasks_cannot_transition(tmp_path):
    store = SQLiteStateStore(tmp_path / "state.db")
    tasks = TaskOrchestrator(store)
    tasks.start("t1")
    tasks.succeed("t1")
    try:
        tasks.start("t1")
        assert False
    except InvalidTaskTransition:
        pass
    store.close()


def test_cancel_is_terminal(tmp_path):
    store = SQLiteStateStore(tmp_path / "state.db")
    tasks = TaskOrchestrator(store)
    cancelled = tasks.cancel("t1")
    assert cancelled.status is TaskStatus.CANCELLED
    try:
        tasks.start("t1")
        assert False
    except InvalidTaskTransition:
        pass
    store.close()
