"""Durable one-time consumption tests for high-risk owner approvals."""
import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.brain_leadership import BrainLeadershipStore


class OwnerApprovalReplayTests(unittest.TestCase):
    def test_challenge_can_be_consumed_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = BrainLeadershipStore(Path(tmp) / "leadership.db")
            try:
                store.consume_owner_approval("challenge-1", "attempt-1", now=100)
                with self.assertRaisesRegex(RuntimeError, "OWNER_APPROVAL_REPLAY"):
                    store.consume_owner_approval("challenge-1", "attempt-2", now=101)
            finally:
                store.close()

    def test_consumption_survives_reopening_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "leadership.db"
            first = BrainLeadershipStore(path)
            first.consume_owner_approval("challenge-persist", "attempt-1", now=100)
            first.close()

            second = BrainLeadershipStore(path)
            try:
                with self.assertRaisesRegex(RuntimeError, "OWNER_APPROVAL_REPLAY"):
                    second.consume_owner_approval("challenge-persist", "attempt-2", now=101)
            finally:
                second.close()

    def test_different_challenges_are_independent(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = BrainLeadershipStore(Path(tmp) / "leadership.db")
            try:
                store.consume_owner_approval("challenge-1", "attempt-1", now=100)
                store.consume_owner_approval("challenge-2", "attempt-2", now=101)
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
