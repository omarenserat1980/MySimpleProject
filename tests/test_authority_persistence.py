from __future__ import annotations

import tempfile
import threading

from platform_foundation.audit_chain import AuditChain
from platform_foundation.authority import AuthorityApprovalLedger
from platform_foundation.lease import TaskLease
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


def test_lease_denial_does_not_consume_irreversible_approval() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        permissions = PermissionBoundary({"delete": ActionRisk.IRREVERSIBLE})
        authority = AuthorityApprovalLedger(state, audit)
        blocker = TaskLease(state, audit)
        holder = blocker.acquire("blocked-task", "existing-owner", ttl_seconds=60)
        assert holder.acquired is True

        supervisor = Supervisor(state, audit, permissions, authority=authority)
        supervisor.register(
            "blocked-task",
            "delete",
            ActionRisk.IRREVERSIBLE,
            lambda: {"deleted": True},
        )
        assert authority.approve(
            "blocked-task", "delete", ActionRisk.IRREVERSIBLE, "human"
        ).approved is True

        result = supervisor.run("blocked-task", lease_ttl_seconds=1)
        assert result.allowed is True
        assert result.status.value == "FAILED"
        assert result.error == "task lease unavailable"
        assert authority.check(
            "blocked-task", "delete", ActionRisk.IRREVERSIBLE
        ).approved is True
        state.close()


def test_concurrent_consumers_can_claim_approval_only_once() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        ledger = AuthorityApprovalLedger(state, audit)
        assert ledger.approve(
            "race-task", "delete", ActionRisk.IRREVERSIBLE, "human"
        ).approved is True

        results = []
        lock = threading.Lock()

        def consume() -> None:
            decision = ledger.consume(
                "race-task", "delete", ActionRisk.IRREVERSIBLE
            )
            with lock:
                results.append(decision.approved)

        threads = [threading.Thread(target=consume) for _ in range(16)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert results.count(True) == 1
        assert results.count(False) == 15
        assert ledger.check(
            "race-task", "delete", ActionRisk.IRREVERSIBLE
        ).approved is False
        assert audit.verify() is True
        state.close()
