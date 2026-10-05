import time

from platform_foundation.audit_chain import AuditChain
from platform_foundation.lease import TaskLease
from platform_foundation.persistent_state import SQLiteStateStore


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
