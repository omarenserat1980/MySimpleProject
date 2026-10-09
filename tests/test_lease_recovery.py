import time

from platform_foundation.audit_chain import AuditChain
from platform_foundation.lease import TaskLease
from platform_foundation.persistent_state import SQLiteStateStore


def test_expired_worker_lease_can_be_recovered(tmp_path):
    state = SQLiteStateStore(tmp_path / 'recovery.sqlite')
    audit = AuditChain()
    lease = TaskLease(state, audit)

    first = lease.acquire('crashed-task', 'dead-worker', ttl_seconds=0.05)
    assert first.acquired
    time.sleep(0.08)

    assert not lease.heartbeat('crashed-task', 'dead-worker').acquired
    recovered = lease.acquire('crashed-task', 'recovery-worker', ttl_seconds=1)
    assert recovered.acquired
    assert lease.release('crashed-task', 'recovery-worker')
    assert audit.verify()
    state.close()