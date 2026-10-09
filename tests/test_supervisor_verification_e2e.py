from __future__ import annotations

import tempfile

from platform_foundation.audit_chain import AuditChain
from platform_foundation.permissions import ActionRisk, PermissionBoundary
from platform_foundation.persistent_state import SQLiteStateStore
from platform_foundation.supervisor import Supervisor
from platform_foundation.task_state import TaskStatus
from platform_foundation.verification import VerificationGate


def test_full_authorize_execute_retry_verify_and_persist_path() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        permissions = PermissionBoundary({"build": ActionRisk.WRITE})
        supervisor = Supervisor(state, audit, permissions)
        verifier = VerificationGate(state, audit)
        calls = {"count": 0}

        def handler() -> dict[str, str]:
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeError("transient")
            return {"artifact": "ready"}

        supervisor.register(
            "e2e-build",
            "build",
            ActionRisk.WRITE,
            handler,
            max_attempts=3,
        )
        execution = supervisor.run("e2e-build")
        assert execution.status is TaskStatus.SUCCESS
        assert execution.attempts == 2

        verification = verifier.verify(
            "e2e-build",
            execution.output,
            lambda value: value == {"artifact": "ready"},
        )
        assert verification.status is TaskStatus.SUCCESS
        assert verification.verified is True

        stored = state.get("verification:e2e-build")
        assert stored["status"] == "SUCCESS"
        assert stored["verified"] is True
        assert audit.verify()

        events = [event.event for event in audit.events()]
        assert "task.permission_denied" not in events
        assert "task.retry" in events
        assert "task.verified" in events
        state.close()
