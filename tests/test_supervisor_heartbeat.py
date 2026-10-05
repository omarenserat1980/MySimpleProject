from __future__ import annotations

import threading
import time

from platform_foundation.audit_chain import AuditChain
from platform_foundation.permissions import ActionRisk, PermissionBoundary
from platform_foundation.persistent_state import SQLiteStateStore
from platform_foundation.supervisor import Supervisor
from platform_foundation.task_state import TaskStatus


def test_long_task_is_kept_alive_by_lease_heartbeat(tmp_path):
    state = SQLiteStateStore(tmp_path / "state.db")
    audit = AuditChain()
    supervisor = Supervisor(state, audit, PermissionBoundary({"read": ActionRisk.READ}))

    def slow():
        time.sleep(0.18)
        return "done"

    supervisor.register("heartbeat-job", "read", ActionRisk.READ, slow, max_attempts=1)
    result = supervisor.run("heartbeat-job", lease_ttl_seconds=0.06)

    assert result.status == TaskStatus.SUCCESS
    assert result.output == "done"
    assert any(event.event == "lease.heartbeat" for event in audit.events())
    assert audit.verify()
    state.close()


def test_lease_loss_cannot_be_reported_as_success(tmp_path):
    state = SQLiteStateStore(tmp_path / "state.db")
    audit = AuditChain()
    supervisor = Supervisor(state, audit, PermissionBoundary({"read": ActionRisk.READ}))
    started = threading.Event()

    def blocked():
        started.set()
        time.sleep(0.20)
        return "must-not-be-success"

    supervisor.register("lost-job", "read", ActionRisk.READ, blocked, max_attempts=1)

    def steal_lease():
        started.wait(1)
        time.sleep(0.08)
        state.set("lease:lost-job", {"owner": "other-worker", "expires_at": time.time() + 10})

    thief = threading.Thread(target=steal_lease)
    thief.start()
    result = supervisor.run("lost-job", lease_ttl_seconds=0.05)
    thief.join()

    assert result.status == TaskStatus.FAILED
    assert result.error == "execution lease lost"
    assert any(event.event == "task.lease_lost" for event in audit.events())
    assert audit.verify()
    state.close()