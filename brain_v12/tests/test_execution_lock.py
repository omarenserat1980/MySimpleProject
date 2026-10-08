import tempfile
import time
import unittest
from pathlib import Path

from brain_v12.brain.execution_lock import BrainExecutionLock, ExecutionLockError


class BrainExecutionLockTests(unittest.TestCase):
    def test_single_flight(self):
        with tempfile.TemporaryDirectory() as td:
            lock = BrainExecutionLock(Path(td) / "execution.lock", lease_seconds=30)
            first = lock.acquire("windows-real-boot")
            self.assertTrue(lock.status()["locked"])
            with self.assertRaisesRegex(ExecutionLockError, "EXECUTION_LOCK_HELD"):
                lock.acquire("another-task")
            lock.release(first)
            self.assertFalse(lock.status()["locked"])

    def test_only_owner_can_release(self):
        with tempfile.TemporaryDirectory() as td:
            lock = BrainExecutionLock(Path(td) / "execution.lock", lease_seconds=30)
            first = lock.acquire("task-a")
            fake = type(first)(
                token="wrong",
                task_id="task-a",
                acquired_at=first.acquired_at,
                expires_at=first.expires_at,
                host=first.host,
                pid=first.pid,
            )
            with self.assertRaisesRegex(ExecutionLockError, "OWNER_MISMATCH"):
                lock.release(fake)
            lock.release(first)

    def test_expired_lease_is_recoverable(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "execution.lock"
            lock = BrainExecutionLock(path, lease_seconds=1)
            first = lock.acquire("stale-task")
            time.sleep(1.1)
            second = lock.acquire("recovery-task")
            self.assertNotEqual(first.token, second.token)
            self.assertEqual(lock.status()["lease"]["task_id"], "recovery-task")
            lock.release(second)

    def test_malformed_lock_is_recovered_only_as_non_active_lease(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "execution.lock"
            path.write_text("{broken", encoding="utf-8")
            lock = BrainExecutionLock(path, lease_seconds=30)
            lease = lock.acquire("recovery")
            self.assertTrue(lock.status()["locked"])
            lock.release(lease)


if __name__ == "__main__":
    unittest.main()
