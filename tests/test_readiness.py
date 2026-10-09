from __future__ import annotations

import tempfile

from platform_foundation.audit_chain import AuditChain
from platform_foundation.permissions import ActionRisk, PermissionBoundary
from platform_foundation.persistent_state import SQLiteStateStore
from platform_foundation.readiness import ReadinessGate


def test_readiness_requires_all_foundation_checks() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        permissions = PermissionBoundary({"build": ActionRisk.WRITE})

        report = ReadinessGate(state, audit, permissions).check()

        assert report.ready is True
        assert report.checks == {
            "state_store": True,
            "audit_chain": True,
            "permission_boundary": True,
        }
        state.close()


def test_tampered_audit_makes_readiness_false() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        permissions = PermissionBoundary({"build": ActionRisk.WRITE})
        audit.record("test", {"value": 1})

        item = audit._events[0]
        object.__setattr__(item, "payload", {"value": 999})

        report = ReadinessGate(state, audit, permissions).check()

        assert report.ready is False
        assert report.checks["state_store"] is True
        assert report.checks["audit_chain"] is False
        assert report.checks["permission_boundary"] is True
        state.close()
