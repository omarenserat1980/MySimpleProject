from __future__ import annotations

import multiprocessing
import tempfile
import time

from platform_foundation.audit_chain import AuditChain
from platform_foundation.permissions import ActionRisk, PermissionBoundary
from platform_foundation.persistent_state import SQLiteStateStore
from platform_foundation.stale_recovery import StaleTaskRecovery
from platform_foundation.supervisor import Supervisor
from platform_integration.brain_supervisor_bridge import BrainSupervisorBridge


def _crashing_worker(db_path: str) -> None:
    state = SQLiteStateStore(db_path)
    supervisor = Supervisor(
        state,
        AuditChain(),
        PermissionBoundary({"build": ActionRisk.WRITE}),
    )
    supervisor.register(
        "crash-restart",
        "build",
        ActionRisk.WRITE,
        lambda: (_ for _ in ()).throw(SystemExit(99)),
        max_attempts=1,
    )
    # The recovery checkpoint is persisted before the handler runs.
    supervisor.run("crash-restart", lease_ttl_seconds=0.25)


def test_full_supervisor_crash_restart_recovery() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        process = multiprocessing.Process(target=_crashing_worker, args=(tmp.name,))
        process.start()
        process.join(timeout=10)
        assert process.exitcode == 99

        state = SQLiteStateStore(tmp.name)
        record = state.get("recovery:crash-restart")
        assert record["status"] == "RUNNING"
        assert record["attempts"] == 1

        time.sleep(0.35)
        audit = AuditChain()
        permissions = PermissionBoundary({"build": ActionRisk.WRITE})
        recovery = StaleTaskRecovery(state, audit)
        recovered = recovery.recover_expired()
        assert [item.task_id for item in recovered] == ["crash-restart"]
        assert recovered[0].status == "RETRYING"
        assert state.get("supervisor:crash-restart")["status"] == "RETRYING"

        bridge = BrainSupervisorBridge(
            state, audit, permissions, root=tmp.name + "-restart"
        )
        result = bridge.execute_verified(
            "crash-restart",
            "build",
            ActionRisk.WRITE,
            lambda: {"artifact": "after-crash"},
            lambda value: value == {"artifact": "after-crash"},
            max_attempts=3,
        )
        assert result.executed is True
        assert result.verified is True
        assert result.status == "SUCCESS"
        assert result.attempts == 2
        assert state.get("recovery:crash-restart")["status"] == "SUCCESS"
        assert bridge.load_verified_execution("crash-restart") is not None
        assert audit.verify()
        state.close()
