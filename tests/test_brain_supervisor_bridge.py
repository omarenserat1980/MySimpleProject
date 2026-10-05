from __future__ import annotations

import tempfile

from brain_v12.brain.brain_supervisor import BrainSupervisor
from platform_foundation.audit_chain import AuditChain
from platform_foundation.permissions import ActionRisk, PermissionBoundary
from platform_foundation.persistent_state import SQLiteStateStore
from platform_integration.brain_supervisor_bridge import BrainSupervisorBridge


def test_brain_supervisor_bridge_requires_foundation_readiness() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        permissions = PermissionBoundary({"supervise": ActionRisk.WRITE})
        bridge = BrainSupervisorBridge(
            state, audit, permissions,
            root=tmp.name + "-brain",
        )

        admission = bridge.admit()
        assert admission.admitted is True
        job = bridge.create_job("integration-smoke")
        assert job["status"] == "running"
        state.close()


def test_bridge_blocks_brain_when_audit_is_tampered() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        permissions = PermissionBoundary({"supervise": ActionRisk.WRITE})
        audit.record("tamper-test", {"value": 1})
        object.__setattr__(audit._events[0], "payload", {"value": 2})

        bridge = BrainSupervisorBridge(
            state, audit, permissions,
            root=tmp.name + "-brain",
        )

        admission = bridge.admit()
        assert admission.admitted is False
        try:
            bridge.create_job("blocked")
        except RuntimeError as exc:
            assert "integration blocked" in str(exc)
        else:
            raise AssertionError("blocked integration was allowed")
        state.close()


def test_bridge_reaches_existing_brain_supervisor_verified_simulation() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        permissions = PermissionBoundary({"supervise": ActionRisk.WRITE})
        bridge = BrainSupervisorBridge(
            state, audit, permissions,
            root=tmp.name + "-brain",
            max_cycles=3,
        )

        result = bridge.simulate_verified_path("verified-integration")
        assert result["status"] == "completed"
        assert result["phase"] == "deliver"
        state.close()
