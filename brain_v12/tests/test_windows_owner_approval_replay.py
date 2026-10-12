"""Durable one-time consumption tests for high-risk owner approvals."""
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
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


    def test_concurrent_consumers_allow_exactly_one_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "leadership.db"
            # Initialize the durable store before starting competing consumers.
            setup = BrainLeadershipStore(path)
            setup.close()
            barrier = Barrier(2)

            def consume(attempt_id):
                store = BrainLeadershipStore(path)
                try:
                    barrier.wait(timeout=5)
                    try:
                        store.consume_owner_approval("challenge-race", attempt_id)
                        return "ACCEPTED"
                    except RuntimeError as exc:
                        if "OWNER_APPROVAL_REPLAY" in str(exc):
                            return "REPLAY_REJECTED"
                        raise
                finally:
                    store.close()

            with ThreadPoolExecutor(max_workers=2) as pool:
                outcomes = list(pool.map(consume, ("attempt-a", "attempt-b")))

            self.assertEqual(outcomes.count("ACCEPTED"), 1, outcomes)
            self.assertEqual(outcomes.count("REPLAY_REJECTED"), 1, outcomes)


if __name__ == "__main__":
    unittest.main()
