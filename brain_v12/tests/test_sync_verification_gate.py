"""Fail-closed end-to-end synchronization verification tests."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.sync_engine import BrainSyncStore
from brain_v12.brain.sync_runtime import DurableSyncQueue, reconcile
from brain_v12.brain.sync_verification_gate import validate_transition, verify_sync_evidence


class TestSyncVerificationGate(unittest.TestCase):
    def test_full_reconnect_replay_reconcile_digest_gate(self):
        with tempfile.TemporaryDirectory() as td:
            local = BrainSyncStore("redmi3-01")
            remote = BrainSyncStore("brain-cloud")
            queue = DurableSyncQueue(Path(td) / "sync.jsonl")
            event = local.put(
                "device/task/t-1",
                {"task_id": "t-1", "status": "COMPLETED", "evidence_ref": "ev-1"},
                event_id="task-event-1",
            )
            self.assertTrue(queue.enqueue(event))

            # Simulate reconnect/replay into the remote replica.
            evidence = reconcile(local, remote, queue)
            result = verify_sync_evidence(
                evidence,
                evidence_ref="ev-1",
                local_digest=local.snapshot()["digest"],
                remote_digest=remote.snapshot()["digest"],
            )
            self.assertEqual(result["status"], "VERIFIED")
            self.assertEqual(result["failures"], [])

            # Replaying the same event is idempotent: no duplicate state mutation.
            duplicate = remote.apply([event])
            self.assertEqual(duplicate["duplicate"], 1)
            self.assertEqual(remote.snapshot()["digest"], local.snapshot()["digest"])

    def test_missing_evidence_ref_fails_closed(self):
        evidence = {
            "queue": {"sent": 1, "acked": 1, "failed": 0},
            "remote_audit_chain_valid": True,
        }
        result = verify_sync_evidence(
            evidence, evidence_ref=None, local_digest="d", remote_digest="d"
        )
        self.assertEqual(result["status"], "VERIFICATION_FAILED")
        self.assertIn("EVIDENCE_REF_REQUIRED", result["failures"])

    def test_digest_mismatch_fails_closed(self):
        evidence = {
            "queue": {"sent": 1, "acked": 1, "failed": 0},
            "remote_audit_chain_valid": True,
        }
        result = verify_sync_evidence(
            evidence, evidence_ref="ev-2", local_digest="local", remote_digest="remote"
        )
        self.assertEqual(result["status"], "VERIFICATION_FAILED")
        self.assertIn("DIGEST_MISMATCH", result["failures"])

    def test_failed_replay_fails_closed(self):
        evidence = {
            "queue": {"sent": 2, "acked": 1, "failed": 1},
            "remote_audit_chain_valid": True,
        }
        result = verify_sync_evidence(
            evidence, evidence_ref="ev-3", local_digest="d", remote_digest="d"
        )
        self.assertEqual(result["status"], "VERIFICATION_FAILED")
        self.assertIn("QUEUE_FAILED", result["failures"])
        self.assertIn("QUEUE_NOT_FULLY_ACKED", result["failures"])

    def test_lifecycle_regression_is_rejected(self):
        self.assertTrue(validate_transition(None, "QUEUED"))
        self.assertTrue(validate_transition("QUEUED", "CLAIMED"))
        self.assertTrue(validate_transition("CLAIMED", "RUNNING"))
        self.assertTrue(validate_transition("RUNNING", "COMPLETED"))
        self.assertFalse(validate_transition("COMPLETED", "RUNNING"))
        self.assertFalse(validate_transition("COMPLETED", "FAILED"))


if __name__ == "__main__":
    unittest.main()
