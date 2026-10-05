from __future__ import annotations

import tempfile

from platform_foundation.audit_chain import AuditChain
from platform_foundation.authority import AuthorityApprovalLedger
from platform_foundation.permissions import ActionRisk, PermissionBoundary
from platform_foundation.persistent_state import SQLiteStateStore
from platform_foundation.supervisor import Supervisor
from platform_integration.brain_supervisor_bridge import BrainSupervisorBridge


def test_irreversible_requires_explicit_persistent_approval() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        audit = AuditChain()
        permissions = PermissionBoundary({"delete": ActionRisk.IRREVERSIBLE})
        state = SQLiteStateStore(tmp.name)
        supervisor = Supervisor(
            state, audit, permissions, authority=AuthorityApprovalLedger(state, audit)
        )
        supervisor.register(
            "irreversible-1",
            "delete",
            ActionRisk.IRREVERSIBLE,
            lambda: {"deleted": True},
        )

        denied = supervisor.run("irreversible-1")
        assert denied.allowed is False
        assert denied.status.value == "FAILED"

        bridge = BrainSupervisorBridge(state, audit, permissions, root=tmp.name + "-brain")
        assert bridge.approve_irreversible("irreversible-1", "delete", "explicit-human-approval")

        approved = bridge.execute_verified(
            "irreversible-1",
            "delete",
            ActionRisk.IRREVERSIBLE,
            lambda: {"deleted": True},
            lambda value: value == {"deleted": True},
        )
        assert approved.executed is True
        assert approved.verified is True
        assert approved.status == "SUCCESS"

        state.close()
        reopened = SQLiteStateStore(tmp.name)
        restart_audit = AuditChain()
        restarted = BrainSupervisorBridge(
            reopened, restart_audit, permissions, root=tmp.name + "-restart"
        )
        assert restarted.authority.check(
            "irreversible-1", "delete", ActionRisk.IRREVERSIBLE
        ).approved is False

        replay = restarted.execute_verified(
            "irreversible-1",
            "delete",
            ActionRisk.IRREVERSIBLE,
            lambda: {"deleted": True},
            lambda value: value == {"deleted": True},
        )
        assert replay.executed is False
        assert replay.verified is False
        assert "approval" in (replay.error or "").lower()
        reopened.close()


def test_approval_cannot_be_replayed_for_different_action() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        ledger = AuthorityApprovalLedger(state, audit)
        approved = ledger.approve(
            "task-a", "delete", ActionRisk.IRREVERSIBLE, "human"
        )
        assert approved.approved is True
        mismatch = ledger.check(
            "task-a", "publish", ActionRisk.IRREVERSIBLE
        )
        assert mismatch.approved is False
        assert "match" in mismatch.reason
        state.close()
