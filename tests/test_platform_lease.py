import multiprocessing
import time

from platform_foundation.audit_chain import AuditChain
from platform_foundation.lease import TaskLease
from platform_foundation.persistent_state import SQLiteStateStore


def _claim(path, owner, start_event, result_queue):
    state = SQLiteStateStore(path)
    audit = AuditChain()
    start_event.wait()
    result = TaskLease(state, audit).acquire("contended", owner, ttl_seconds=5)
    result_queue.put(result.acquired)
    state.close()


def test_lease_blocks_competing_owner_and_allows_expiry(tmp_path):
    state = SQLiteStateStore(tmp_path / "lease.sqlite")
    audit = AuditChain()
    lease = TaskLease(state, audit)

    first = lease.acquire("task-1", "worker-a", ttl_seconds=0.05)
    assert first.acquired
    assert not lease.acquire("task-1", "worker-b", ttl_seconds=1).acquired

    assert lease.heartbeat("task-1", "worker-a", ttl_seconds=0.05).acquired
    assert not lease.heartbeat("task-1", "worker-b").acquired

    time.sleep(0.07)
    expired = lease.acquire("task-1", "worker-b", ttl_seconds=1)
    assert expired.acquired
    assert not lease.release("task-1", "worker-a")
    assert lease.release("task-1", "worker-b")
    assert audit.verify()
    state.close()


def test_lease_survives_reopen(tmp_path):
    path = tmp_path / "lease-reopen.sqlite"
    state = SQLiteStateStore(path)
    audit = AuditChain()
    lease = TaskLease(state, audit)

    assert lease.acquire("task-2", "worker-a", ttl_seconds=10).acquired
    state.close()

    reopened = SQLiteStateStore(path)
    reopened_lease = TaskLease(reopened, audit)
    assert not reopened_lease.acquire("task-2", "worker-b", ttl_seconds=10).acquired
    assert reopened_lease.release("task-2", "worker-a")
    assert audit.verify()
    reopened.close()


def test_lease_allows_only_one_concurrent_owner(tmp_path):
    path = str(tmp_path / "concurrent.sqlite")
    state = SQLiteStateStore(path)
    state.close()

    ctx = multiprocessing.get_context("spawn")
    start_event = ctx.Event()
    result_queue = ctx.Queue()
    processes = [
        ctx.Process(target=_claim, args=(path, "worker-a", start_event, result_queue)),
        ctx.Process(target=_claim, args=(path, "worker-b", start_event, result_queue)),
    ]
    for process in processes:
        process.start()
    start_event.set()
    results = [result_queue.get(timeout=10) for _ in processes]
    for process in processes:
        process.join(timeout=10)
    assert all(not process.exitcode for process in processes)
    assert sum(results) == 1
