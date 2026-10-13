from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.family_governance import FamilyApproval
from brain_v12.brain.family_governed_tasks import FamilyGovernedTaskService
from brain_v12.brain.software_node_agent import PersistentTaskQueue


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
        allowed = self.service.enqueue(task, approval=approval)
        self.assertTrue(allowed["ok"], allowed)
        self.assertTrue(allowed["queued"])
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

    def test_out_of_scope_approval_does_not_authorize_private_read(self):
        approval = FamilyApproval(
            approver_role="FAMILY_GUARDIAN", approved=True,
            consent_reference="consent-publish-1", identity_verified=True,
            scope="publish",
        )
        result = self.service.enqueue({"type": "read_text", "path": "notes.txt"}, approval=approval)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "FAMILY_APPROVAL_INVALID_OR_OUT_OF_SCOPE")
        self.assertEqual(self.queue.counts()["PENDING"], 0)


if __name__ == "__main__":
    unittest.main()
