from __future__ import annotations

import tempfile

from platform_foundation.audit_chain import AuditChain
from platform_foundation.permissions import ActionRisk, PermissionBoundary
from platform_foundation.persistent_state import SQLiteStateStore
from platform_integration.brain_supervisor_bridge import BrainSupervisorBridge


def test_verified_recovery_survives_process_reopen() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        audit = AuditChain()
        permissions = PermissionBoundary({"build": ActionRisk.WRITE})

        state = SQLiteStateStore(tmp.name)
        first = BrainSupervisorBridge(
            state, audit, permissions, root=tmp.name + "-first"
        )

        def interrupted():
            raise RuntimeError("interrupted")

        result1 = first.execute_verified(
            "reopen-recovery",
            "build",
            ActionRisk.WRITE,
            interrupted,
            lambda _: True,
            max_attempts=1,
        )
        assert result1.executed is False
        assert result1.status == "FAILED"
        assert state.get("recovery:reopen-recovery")["attempts"] == 1
        state.close()

        reopened = SQLiteStateStore(tmp.name)
        second = BrainSupervisorBridge(
            reopened, audit, permissions, root=tmp.name + "-second"
        )

        result2 = second.execute_verified(
            "reopen-recovery",
            "build",
            ActionRisk.WRITE,
            lambda: {"artifact": "recovered"},
            lambda value: value == {"artifact": "recovered"},
            max_attempts=3,
        )
        assert result2.executed is True
        assert result2.verified is True
        assert result2.status == "SUCCESS"
        assert result2.attempts == 2
        assert reopened.get("recovery:reopen-recovery")["status"] == "SUCCESS"
        assert reopened.get("verification:reopen-recovery")["verified"] is True
        assert audit.verify()
        reopened.close()


def test_verified_execution_can_be_recovered_without_reexecution() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        audit = AuditChain()
        permissions = PermissionBoundary({"build": ActionRisk.WRITE})
        state = SQLiteStateStore(tmp.name)
        first = BrainSupervisorBridge(
            state, audit, permissions, root=tmp.name + "-first"
        )

        result = first.execute_verified(
            "durable-verified",
            "build",
            ActionRisk.WRITE,
            lambda: {"artifact": "proof"},
            lambda value: value == {"artifact": "proof"},
        )
        assert result.executed is True
        assert result.verified is True

        state.close()
        reopened = SQLiteStateStore(tmp.name)
        second = BrainSupervisorBridge(
            reopened, audit, permissions, root=tmp.name + "-second"
        )

        recovered = second.load_verified_execution("durable-verified")
        assert recovered is not None
        assert recovered.executed is True
        assert recovered.verified is True
        assert recovered.status == "SUCCESS"
        assert recovered.attempts == 1

        tampered = reopened.get("brain_bridge:durable-verified")
        tampered["verified"] = False
        reopened.set("brain_bridge:durable-verified", tampered)
        assert second.load_verified_execution("durable-verified") is None

        reopened.close()
