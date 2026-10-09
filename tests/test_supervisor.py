from __future__ import annotations

import tempfile

from platform_foundation.audit_chain import AuditChain
from platform_foundation.permissions import ActionRisk, PermissionBoundary
from platform_foundation.persistent_state import SQLiteStateStore
from platform_foundation.supervisor import Supervisor
from platform_foundation.task_state import TaskStatus


def test_supervisor_executes_authorized_task_with_retry() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        permissions = PermissionBoundary({"build": ActionRisk.WRITE})
        supervisor = Supervisor(state, audit, permissions)
        calls = {"count": 0}

        def handler() -> str:
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeError("temporary")
            return "artifact-ready"

        supervisor.register("job-1", "build", ActionRisk.WRITE, handler, max_attempts=3)
        result = supervisor.run("job-1")

        assert result.status is TaskStatus.SUCCESS
        assert result.allowed is True
        assert result.attempts == 2
        assert result.output == "artifact-ready"
        assert state.get("supervisor:job-1")["status"] == "SUCCESS"
        assert audit.verify()
        state.close()


def test_supervisor_denies_unknown_action() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        permissions = PermissionBoundary()
        supervisor = Supervisor(state, audit, permissions)

        supervisor.register("job-2", "unknown", ActionRisk.WRITE, lambda: "must-not-run")
        result = supervisor.run("job-2")

        assert result.status is TaskStatus.FAILED
        assert result.allowed is False
        assert result.attempts == 0
        assert "allowlisted" in (result.error or "")
        state.close()


def test_supervisor_denies_irreversible_action() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        permissions = PermissionBoundary({"delete": ActionRisk.IRREVERSIBLE})
        supervisor = Supervisor(state, audit, permissions)

        supervisor.register("job-3", "delete", ActionRisk.IRREVERSIBLE, lambda: "must-not-run")
        result = supervisor.run("job-3")

        assert result.status is TaskStatus.FAILED
        assert result.allowed is False
        assert result.attempts == 0
        assert "irreversible" in (result.error or "")
        state.close()
