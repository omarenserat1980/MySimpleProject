from __future__ import annotations

import tempfile

from brain_v12.brain.brain_supervisor import BrainSupervisor
from platform_foundation.audit_chain import AuditChain
from platform_foundation.durable_audit import SQLiteAuditChain
from platform_foundation.permissions import ActionRisk, PermissionBoundary
from platform_foundation.persistent_state import SQLiteStateStore
from platform_integration.brain_supervisor_bridge import BrainSupervisorBridge


def test_brain_supervisor_bridge_requires_foundation_readiness() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        permissions = PermissionBoundary({"supervise": ActionRisk.WRITE})
        bridge = BrainSupervisorBridge(state, audit, permissions, root=tmp.name + "-brain")
        assert bridge.admit().admitted is True
        assert bridge.create_job("integration-smoke")["status"] == "running"
        state.close()


def test_bridge_blocks_brain_when_audit_is_tampered() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        permissions = PermissionBoundary({"supervise": ActionRisk.WRITE})
        audit.record("tamper-test", {"value": 1})
        object.__setattr__(audit._events[0], "payload", {"value": 2})
        bridge = BrainSupervisorBridge(state, audit, permissions, root=tmp.name + "-brain")
        assert bridge.admit().admitted is False
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
        bridge = BrainSupervisorBridge(state, audit, permissions, root=tmp.name + "-brain", max_cycles=3)
        result = bridge.simulate_verified_path("verified-integration")
        assert result["status"] == "completed"
        assert result["phase"] == "deliver"
        state.close()


def test_bridge_requires_independent_verification_before_reporting_success() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        permissions = PermissionBoundary({"build": ActionRisk.WRITE})
        bridge = BrainSupervisorBridge(state, audit, permissions, root=tmp.name + "-brain")
        result = bridge.execute_verified(
            "verified-execution", "build", ActionRisk.WRITE,
            lambda: {"artifact": "real-output"},
            lambda output: output == {"artifact": "real-output"},
        )
        assert result.executed is True
        assert result.verified is True
        assert result.status == "SUCCESS"
        assert state.get("verification:verified-execution")["verified"] is True
        assert state.get("brain_bridge:verified-execution")["verified"] is True
        state.close()


def test_bridge_rejects_unverified_output_even_after_execution() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        permissions = PermissionBoundary({"build": ActionRisk.WRITE})
        bridge = BrainSupervisorBridge(state, audit, permissions, root=tmp.name + "-brain")
        result = bridge.execute_verified(
            "unverified-execution", "build", ActionRisk.WRITE,
            lambda: {"artifact": "bad-output"},
            lambda output: output == {"artifact": "expected-output"},
        )
        assert result.executed is True
        assert result.verified is False
        assert result.status == "FAILED"
        assert state.get("brain_bridge:unverified-execution")["verified"] is False
        state.close()


def test_bridge_denies_irreversible_execution_before_handler() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        permissions = PermissionBoundary({"publish": ActionRisk.IRREVERSIBLE})
        bridge = BrainSupervisorBridge(state, audit, permissions, root=tmp.name + "-brain")
        called = {"value": False}

        def handler():
            called["value"] = True
            return "should-not-run"

        result = bridge.execute_verified(
            "blocked-execution", "publish", ActionRisk.IRREVERSIBLE,
            handler, lambda _: True,
        )
        assert result.executed is False
        assert result.verified is False
        assert called["value"] is False
        assert result.status == "FAILED"
        state.close()


def test_bridge_recovers_after_process_restart_and_keeps_durable_evidence() -> None:
    with tempfile.TemporaryDirectory() as root:
        state_path = root + "/state.db"
        audit_path = root + "/audit.db"
        permissions = PermissionBoundary({"build": ActionRisk.WRITE})
        calls = {"count": 0}

        def flaky_handler():
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeError("simulated process interruption")
            return {"artifact": "recovered"}

        state1 = SQLiteStateStore(state_path)
        audit1 = SQLiteAuditChain(audit_path)
        bridge1 = BrainSupervisorBridge(
            state1, audit1, permissions, root=root + "/brain"
        )
        first = bridge1.execute_verified(
            "restart-recovery", "build", ActionRisk.WRITE,
            flaky_handler, lambda output: output == {"artifact": "recovered"},
            max_attempts=1,
        )
        assert first.executed is False
        assert first.verified is False
        assert first.status == "FAILED"
        state1.close()
        audit1.close()

        state2 = SQLiteStateStore(state_path)
        audit2 = SQLiteAuditChain(audit_path)
        bridge2 = BrainSupervisorBridge(
            state2, audit2, permissions, root=root + "/brain"
        )
        second = bridge2.execute_verified(
            "restart-recovery", "build", ActionRisk.WRITE,
            flaky_handler, lambda output: output == {"artifact": "recovered"},
            max_attempts=3,
        )
        assert second.executed is True
        assert second.verified is True
        assert second.status == "SUCCESS"
        assert second.attempts == 2
        assert state2.get("recovery:restart-recovery")["status"] == "SUCCESS"
        assert state2.get("verification:restart-recovery")["verified"] is True
        assert audit2.verify() is True
        assert len(audit2.events()) >= 6
        state2.close()
        audit2.close()
