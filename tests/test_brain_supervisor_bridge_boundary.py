from __future__ import annotations

import tempfile

from platform_foundation.audit_chain import AuditChain
from platform_foundation.permissions import ActionRisk, PermissionBoundary
from platform_foundation.persistent_state import SQLiteStateStore
from platform_integration.brain_supervisor_bridge import BrainSupervisorBridge


def test_bridge_never_calls_supervisor_when_admission_fails() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        permissions = PermissionBoundary({"supervise": ActionRisk.WRITE})

        audit.record("tamper-test", {"value": "original"})
        object.__setattr__(audit._events[0], "payload", {"value": "tampered"})

        bridge = BrainSupervisorBridge(
            state, audit, permissions,
            root=tmp.name + "-brain",
        )

        original = bridge.supervisor.create

        def forbidden(*args, **kwargs):
            raise AssertionError("Brain Supervisor must not be called")

        bridge.supervisor.create = forbidden
        try:
            try:
                bridge.create_job("must-be-blocked")
            except RuntimeError:
                pass
        finally:
            bridge.supervisor.create = original

        state.close()
