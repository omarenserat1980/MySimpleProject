from __future__ import annotations

import time

from platform_foundation.audit_chain import AuditChain
from platform_foundation.permissions import ActionRisk, PermissionBoundary
from platform_foundation.persistent_state import SQLiteStateStore
from platform_foundation.stale_recovery import StaleTaskRecovery
from platform_foundation.supervisor import Supervisor
from platform_foundation.task_state import TaskStatus


def test_expired_running_task_is_recovered(tmp_path):
    state = SQLiteStateStore(tmp_path / "state.db")
    audit = AuditChain()
    supervisor = Supervisor(state, audit, PermissionBoundary({"read": ActionRisk.READ}))
    supervisor.register("stale-1", "read", ActionRisk.READ, lambda: "ok")
    state.set("supervisor:stale-1", {
        **state.get("supervisor:stale-1"),
        "status": TaskStatus.RUNNING.value,
    })
    state.set("lease:stale-1", {"owner": "dead-worker", "expires_at": time.time() - 1})

    recovered = StaleTaskRecovery(state, audit).recover_expired()

    assert [item.task_id for item in recovered] == ["stale-1"]
    assert state.get("supervisor:stale-1")["status"] == TaskStatus.RETRYING.value
    assert any(event.event == "task.stale_recovered" for event in audit.events())
    state.close()


def test_active_running_task_is_not_recovered(tmp_path):
    state = SQLiteStateStore(tmp_path / "state.db")
    audit = AuditChain()
    state.set("supervisor:active-1", {"task_id": "active-1", "status": TaskStatus.RUNNING.value})
    state.set("lease:active-1", {"owner": "live-worker", "expires_at": time.time() + 60})

    recovered = StaleTaskRecovery(state, audit).recover_expired()

    assert recovered == []
    assert state.get("supervisor:active-1")["status"] == TaskStatus.RUNNING.value
    state.close()


def test_recovered_task_can_be_reclaimed_by_new_supervisor(tmp_path):
    state = SQLiteStateStore(tmp_path / "state.db")
    audit = AuditChain()
    permissions = PermissionBoundary({"read": ActionRisk.READ})
    state.set("supervisor:crashed-1", {
        "task_id": "crashed-1", "action": "read", "risk": "READ",
        "status": TaskStatus.RUNNING.value, "max_attempts": 1,
    })
    state.set("lease:crashed-1", {"owner": "crashed-worker", "expires_at": time.time() - 1})
    StaleTaskRecovery(state, audit).recover_expired()

    fresh = Supervisor(state, audit, permissions)
    fresh.register("crashed-1", "read", ActionRisk.READ, lambda: "recovered")
    result = fresh.run("crashed-1", lease_ttl_seconds=30)

    assert result.status == TaskStatus.SUCCESS
    assert result.output == "recovered"
    assert state.get("supervisor:crashed-1")["status"] == TaskStatus.SUCCESS.value
    assert audit.verify()
    state.close()