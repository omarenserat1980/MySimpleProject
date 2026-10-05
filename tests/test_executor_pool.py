import threading
import time

from platform_foundation.audit_chain import AuditChain
from platform_foundation.execution_policy import ExecutorDescriptor
from platform_foundation.executor_pool import BrainExecutorPool
from platform_foundation.persistent_state import SQLiteStateStore


def make(tmp_path, executors=None):
    store = SQLiteStateStore(tmp_path / "state.db")
    audit = AuditChain()
    pool = BrainExecutorPool(
        store,
        audit,
        executors or [
            ExecutorDescriptor(
                "brain-local-01",
                "brain",
                True,
                frozenset({"python"}),
            )
        ],
    )
    return pool, store, audit


def test_brain_pool_executes_and_verifies(tmp_path):
    pool, store, audit = make(tmp_path)
    pool.register(
        "echo",
        lambda job: {"job": job.job_id},
        lambda job, out: out["job"] == job.job_id,
    )
    pool.submit("job-1", "echo")

    result = pool.dispatch("job-1")
    assert result.status == "SUCCESS"
    assert result.executor_id == "brain-local-01"
    assert result.output == {"job": "job-1"}
    assert audit.verify()
    store.close()


def test_windows_is_optional_and_brain_continues(tmp_path):
    pool, store, audit = make(
        tmp_path,
        [
            ExecutorDescriptor(
                "brain-local-01", "brain", True, frozenset({"python"})
            ),
            ExecutorDescriptor(
                "arkan-windows", "windows", True, frozenset({"python"})
            ),
        ],
    )
    pool.register("echo", lambda job: "ok", lambda job, out: out == "ok")
    pool.submit("job-optional-windows", "echo")

    result = pool.dispatch("job-optional-windows")
    assert result.status == "SUCCESS"
    assert result.executor_id == "brain-local-01"
    assert audit.verify()
    store.close()


def test_external_runner_cannot_replace_brain(tmp_path):
    pool, store, audit = make(
        tmp_path,
        [ExecutorDescriptor("github-hosted", "github", False, frozenset({"python"}))],
    )
    called = []

    pool.register(
        "echo",
        lambda job: called.append(True) or "must-not-run",
        lambda job, out: True,
    )
    pool.submit("job-no-brain", "echo")

    result = pool.dispatch("job-no-brain")
    assert result.status == "BLOCKED"
    assert result.executor_id is None
    assert "fallback forbidden" in (result.error or "")
    assert not called
    store.close()


def test_expired_lease_recovers_and_fences_old_owner(tmp_path):
    pool, store, audit = make(tmp_path)
    pool.register(
        "slow",
        lambda job: "default",
        lambda job, out: out in {"old", "new"},
    )
    pool.submit("job-recover", "slow")

    old_started = threading.Event()
    old_release = threading.Event()
    old_result = []

    def old_handler(job):
        old_started.set()
        old_release.wait(timeout=2)
        return "old"

    pool.handlers["slow"] = old_handler

    old_thread = threading.Thread(
        target=lambda: old_result.append(
            pool.dispatch(
                "job-recover",
                lease_ttl_seconds=0.03,
                owner_id="executor:brain-local-01:old",
            )
        )
    )
    old_thread.start()
    assert old_started.wait(timeout=2)

    time.sleep(0.05)

    def new_handler(job):
        return "new"

    pool.handlers["slow"] = new_handler
    new_result = pool.dispatch(
        "job-recover",
        lease_ttl_seconds=1.0,
        owner_id="executor:brain-local-01:new",
    )

    assert new_result.status == "SUCCESS"
    assert new_result.output == "new"
    assert pool.current("job-recover").output == "new"

    old_release.set()
    old_thread.join(timeout=2)
    assert old_result[0].status == "SUCCESS" or old_result[0].status == "RUNNING"
    assert pool.current("job-recover").output == "new"
    assert audit.verify()
    store.close()
