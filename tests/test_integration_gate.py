from __future__ import annotations

import tempfile

from platform_foundation.audit_chain import AuditChain
from platform_foundation.integration_gate import IntegrationGate
from platform_foundation.permissions import ActionRisk, PermissionBoundary
from platform_foundation.persistent_state import SQLiteStateStore


def test_integration_is_admitted_when_foundation_is_ready() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        permissions = PermissionBoundary({"build": ActionRisk.WRITE})

        result = IntegrationGate(state, audit, permissions).admit()

        assert result.admitted is True
        assert result.reason == "foundation ready for higher-level integration"
        state.close()


def test_integration_is_blocked_when_audit_is_tampered() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        permissions = PermissionBoundary({"build": ActionRisk.WRITE})
        audit.record("test", {"value": 1})
        object.__setattr__(audit._events[0], "payload", {"value": 2})

        result = IntegrationGate(state, audit, permissions).admit()

        assert result.admitted is False
        assert result.reason == "foundation readiness gate failed"
        assert result.checks["audit_chain"] is False
        state.close()
