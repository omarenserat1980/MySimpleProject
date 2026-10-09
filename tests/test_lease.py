from __future__ import annotations

import tempfile
import time

from platform_foundation.audit_chain import AuditChain
from platform_foundation.lease import TaskLease
from platform_foundation.persistent_state import SQLiteStateStore


def test_only_one_owner_can_hold_active_lease() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        lease = TaskLease(state, audit)

        first = lease.acquire("job-1", "worker-a", ttl_seconds=60)
        second = lease.acquire("job-1", "worker-b", ttl_seconds=60)

        assert first.acquired is True
        assert second.acquired is False
        assert lease.is_owned("job-1", "worker-a")
        assert not lease.is_owned("job-1", "worker-b")
        assert audit.verify()
        state.close()


def test_expired_lease_can_be_recovered_by_new_owner() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        lease = TaskLease(state, audit)

        first = lease.acquire("job-2", "worker-a", ttl_seconds=0.01)
        assert first.acquired is True
        time.sleep(0.03)

        recovered = lease.acquire("job-2", "worker-b", ttl_seconds=60)
        assert recovered.acquired is True
        assert lease.is_owned("job-2", "worker-b")
        assert not lease.is_owned("job-2", "worker-a")
        state.close()


def test_stale_worker_cannot_heartbeat_or_release_new_owner_lease() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        lease = TaskLease(state, audit)

        old = lease.acquire("job-3", "worker-a", ttl_seconds=0.01)
        time.sleep(0.03)
        new = lease.acquire("job-3", "worker-b", ttl_seconds=60)

        stale_heartbeat = lease.heartbeat("job-3", "worker-a")
        stale_release = lease.release("job-3", "worker-a")

        assert old.acquired is True
        assert new.acquired is True
        assert stale_heartbeat.acquired is False
        assert stale_release is False
        assert lease.is_owned("job-3", "worker-b")
        assert audit.verify()
        state.close()


def test_release_allows_next_owner_without_duplicate_active_execution() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        lease = TaskLease(state, audit)

        first = lease.acquire("job-4", "worker-a", ttl_seconds=60)
        assert first.acquired is True
        assert lease.release("job-4", "worker-a") is True

        second = lease.acquire("job-4", "worker-b", ttl_seconds=60)
        assert second.acquired is True
        assert lease.is_owned("job-4", "worker-b")
        assert audit.verify()
        state.close()
