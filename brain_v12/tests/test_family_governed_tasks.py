from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.family_governance import FamilyApproval
from brain_v12.brain.family_governed_tasks import FamilyGovernedTaskService
from brain_v12.brain.family_policy_audit import FamilyPolicyAudit
from brain_v12.brain.software_node_agent import PersistentTaskQueue, SoftwareNodeAgent


class TestOnlyApprovalVerifier:
    """Test seam only; never use as a production identity provider."""
    def verify(self, *, approval, action, task_fingerprint):
        return (
            approval.approved
            and approval.approver_role == "FAMILY_GUARDIAN"
            and approval.identity_verified
            and bool(approval.consent_reference)
            and approval.scope == action
            and bool(task_fingerprint)
        )


class FamilyGovernedTaskServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.queue = PersistentTaskQueue(Path(self.tmp.name) / "queue.sqlite3")
        self.service = FamilyGovernedTaskService(self.queue)

    def tearDown(self):
        self.tmp.cleanup()

    def test_low_risk_health_check_can_be_queued_without_approval(self):
        result = self.service.enqueue({"type": "health_check"})
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["queued"])
        self.assertEqual(self.queue.counts()["PENDING"], 1)
        self.assertEqual(self.service.audit_log[-1]["event"], "FAMILY_POLICY_DECISION")

    def test_private_file_read_requires_scoped_guardian_approval(self):
        task = {"type": "read_text", "path": "notes.txt"}
        denied = self.service.enqueue(task)
        self.assertFalse(denied["ok"])
        self.assertEqual(denied["status"], "FAMILY_APPROVAL_REQUIRED")
        self.assertFalse(denied["queued"])
        self.assertEqual(self.queue.counts()["PENDING"], 0)

        approval = FamilyApproval(
            approver_role="FAMILY_GUARDIAN", approved=True,
            consent_reference="consent-read-1", identity_verified=True,
            scope="read_private_data",
        )
        self.service = FamilyGovernedTaskService(self.queue, approval_verifier=TestOnlyApprovalVerifier())
        allowed = self.service.enqueue(task, approval=approval)
        self.assertTrue(allowed["ok"], allowed)
        self.assertTrue(allowed["queued"])
        self.assertEqual(self.queue.counts()["PENDING"], 1)

    def test_default_verifier_rejects_self_asserted_identity(self):
        approval = FamilyApproval(
            approver_role="FAMILY_GUARDIAN", approved=True,
            consent_reference="self-asserted", identity_verified=True,
            scope="read_private_data",
        )
        result = self.service.enqueue({"type": "read_text", "path": "private.txt"}, approval=approval)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "FAMILY_APPROVAL_REQUIRED")
        self.assertEqual(self.queue.counts()["PENDING"], 0)

    def test_audit_chain_survives_service_recreation(self):
        self.service.enqueue({"type": "health_check"})
        audit = FamilyPolicyAudit(Path(self.tmp.name) / "queue.sqlite3")
        self.assertTrue(audit.verify()["ok"])
        self.assertEqual(audit.verify()["checked"], 1)

    def test_audit_chain_detects_event_tampering(self):
        self.service.enqueue({"type": "health_check"})
        with sqlite3.connect(Path(self.tmp.name) / "queue.sqlite3") as db:
            db.execute("UPDATE family_policy_audit SET event_json='{}' WHERE sequence=1")
        result = self.service.audit_status()
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "AUDIT_EVENT_HASH_MISMATCH")

    def test_approval_reference_cannot_be_replayed(self):
        task = {"type": "read_text", "path": "notes.txt"}
        approval = FamilyApproval(
            approver_role="FAMILY_GUARDIAN", approved=True,
            consent_reference="one-time-consent", identity_verified=True,
            scope="read_private_data",
        )
        self.service = FamilyGovernedTaskService(self.queue, approval_verifier=TestOnlyApprovalVerifier())
        first = self.service.enqueue(task, approval=approval)
        second = self.service.enqueue(task, approval=approval)
        self.assertTrue(first["ok"], first)
        self.assertFalse(second["ok"])
        self.assertEqual(second["status"], "FAMILY_APPROVAL_REPLAY_BLOCKED")
        self.assertEqual(self.queue.counts()["PENDING"], 1)

    def test_medium_risk_brainvm_requires_approval_if_irreversible(self):
        result = self.service.enqueue({"type": "run_brainvm", "program": []})
        # The family gate approves this bounded task as medium risk; task-specific
        # validation remains the queue/executor's responsibility.
        self.assertTrue(result["ok"], result)

    def test_disallowed_task_never_enters_queue(self):
        result = self.service.enqueue({"type": "shell", "command": "whoami"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "TASK_TYPE_NOT_ALLOWED")
        self.assertEqual(self.queue.counts()["PENDING"], 0)
        self.assertEqual(self.service.audit_log[-1]["event"], "FAMILY_POLICY_DENIAL")

    def test_agent_public_enqueue_uses_family_gate(self):
        agent = SoftwareNodeAgent(
            Path(self.tmp.name) / "agent-workspace",
            database_path=Path(self.tmp.name) / "agent.sqlite3",
        )
        accepted = agent.enqueue({"type": "health_check"})
        denied = agent.enqueue({"type": "read_text", "path": "private.txt"})
        self.assertTrue(accepted["ok"], accepted)
        self.assertFalse(denied["ok"], denied)
        self.assertEqual(denied["status"], "FAMILY_APPROVAL_REQUIRED")
        self.assertEqual(agent.status()["family_policy_gate"], "ENFORCED_BY_AGENT_ENQUEUE_FACADE")
        self.assertEqual(agent.queue.counts()["PENDING"], 1)

    def test_out_of_scope_approval_does_not_authorize_private_read(self):
        approval = FamilyApproval(
            approver_role="FAMILY_GUARDIAN", approved=True,
            consent_reference="consent-publish-1", identity_verified=True,
            scope="publish",
        )
        self.service = FamilyGovernedTaskService(self.queue, approval_verifier=TestOnlyApprovalVerifier())
        result = self.service.enqueue({"type": "read_text", "path": "notes.txt"}, approval=approval)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "FAMILY_APPROVAL_INVALID_OR_OUT_OF_SCOPE")
        self.assertEqual(self.queue.counts()["PENDING"], 0)


if __name__ == "__main__":
    unittest.main()
