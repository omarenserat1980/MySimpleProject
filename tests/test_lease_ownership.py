from __future__ import annotations

import time

from platform_foundation.audit_chain import AuditChain
from platform_foundation.lease import TaskLease
from platform_foundation.persistent_state import SQLiteStateStore


def test_ownership_is_false_after_expiry(tmp_path):
    state = SQLiteStateStore(tmp_path / "state.db")
    audit = AuditChain()
    lease = TaskLease(state, audit)
    result = lease.acquire("job", "worker", ttl_seconds=1)
    assert result.acquired
    assert lease.is_owned("job", "worker")
    assert not lease.is_owned("job", "worker", now=time.time() + 2)
    state.close()


def test_old_owner_cannot_heartbeat_after_reclaim(tmp_path):
    state = SQLiteStateStore(tmp_path / "state.db")
    audit = AuditChain()
    lease = TaskLease(state, audit)
    first = lease.acquire("job", "old", ttl_seconds=1)
    assert first.acquired
    second = lease.acquire("job", "new", ttl_seconds=1, )
    assert not second.acquired
    state.set("lease:job", {"owner": "old", "expires_at": time.time() - 1})
    reclaimed = lease.acquire("job", "new", ttl_seconds=30)
    assert reclaimed.acquired
    assert not lease.heartbeat("job", "old", ttl_seconds=30).acquired
    assert lease.is_owned("job", "new")
    assert audit.verify()
    state.close()