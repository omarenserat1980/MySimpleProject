from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from brain_v12.brain.software_node_agent import PersistentTaskQueue, SoftwareNodeAgent


class PersistentTaskQueueTests(unittest.TestCase):
    def test_queue_survives_reopen_and_preserves_pending_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "queue.sqlite3"
            first = PersistentTaskQueue(db)
            accepted = first.enqueue({"type": "health_check"})
            second = PersistentTaskQueue(db)
            stored = second.get(accepted["task_id"])
            self.assertEqual(stored["status"], "PENDING")
            self.assertEqual(stored["task"], {"type": "health_check"})

    def test_idempotency_key_deduplicates_retries(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue = PersistentTaskQueue(Path(tmp) / "queue.sqlite3")
            first = queue.enqueue({"type": "health_check"}, idempotency_key="health-001")
            second = queue.enqueue({"type": "health_check"}, idempotency_key="health-001")
            self.assertEqual(first["task_id"], second["task_id"])
            self.assertFalse(first["deduplicated"])
            self.assertTrue(second["deduplicated"])
            self.assertEqual(queue.counts()["PENDING"], 1)

    def test_disallowed_task_is_rejected_before_persistence(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue = PersistentTaskQueue(Path(tmp) / "queue.sqlite3")
            with self.assertRaisesRegex(ValueError, "TASK_TYPE_NOT_ALLOWED"):
                queue.enqueue({"type": "shell", "command": "whoami"})
            self.assertEqual(queue.counts()["PENDING"], 0)

    def test_agent_executes_and_persists_task_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            db = Path(tmp) / "state" / "queue.sqlite3"
            agent = SoftwareNodeAgent(root, database_path=db, heartbeat_interval=0.05)
            queued = agent.queue.enqueue(
                {"type": "write_text", "path": "result.txt", "content": "durable"},
                idempotency_key="write-result",
            )
            self.assertEqual(agent.run_once()["status"], "AGENT_NOT_STARTED")
            agent.start()
            processed = agent.run_once()
            self.assertTrue(processed["ok"], processed)
            record = agent.queue.get(queued["task_id"])
            self.assertEqual(record["status"], "COMPLETED")
            self.assertTrue(record["result"]["ok"])
            self.assertEqual((root / "result.txt").read_text(encoding="utf-8"), "durable")
            self.assertEqual(agent.status()["queue"]["COMPLETED"], 1)
            agent.stop()

    def test_continuous_heartbeat_is_persisted_and_stop_is_cooperative(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = SoftwareNodeAgent(
                Path(tmp) / "workspace",
                database_path=Path(tmp) / "state.sqlite3",
                heartbeat_interval=0.03,
            )
            started = agent.start()
            initial = started["heartbeat"]["sequence"]
            time.sleep(0.12)
            live = agent.status()
            self.assertGreater(live["heartbeat"]["sequence"], initial)
            self.assertEqual(live["agent_state"], "RUNNING_SIMULATED")
            self.assertFalse(live["physical_host_contacted"])
            stopped = agent.stop()
            self.assertEqual(stopped["agent_state"], "STOPPED")
            self.assertEqual(stopped["heartbeat"]["state"], "STOPPED")
            self.assertFalse(stopped["windows_server_2025_boot_verified"])

    def test_expired_task_lease_returns_task_to_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue = PersistentTaskQueue(Path(tmp) / "queue.sqlite3", lease_seconds=0.05)
            queued = queue.enqueue({"type": "health_check"})
            claimed = queue.claim()
            self.assertEqual(claimed["task_id"], queued["task_id"])
            self.assertEqual(queue.get(queued["task_id"])["status"], "RUNNING")
            time.sleep(0.08)
            reclaimed = queue.claim()
            self.assertEqual(reclaimed["task_id"], queued["task_id"])
            self.assertEqual(reclaimed["attempt"], 2)
            self.assertNotEqual(reclaimed["lease_token"], claimed["lease_token"])


if __name__ == "__main__":
    unittest.main()
