import tempfile
import unittest
from pathlib import Path

from brain_v12.home_server import HomeServerStore
from brain_v12.local_worker_proof_bridge import run_once


class LocalWorkerProofBridgeTests(unittest.TestCase):
    def test_worker_result_is_accepted_by_execution_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = HomeServerStore(Path(tmp) / "home.sqlite3")
            created = store.enqueue("platform", {}, "bridge-1")
            report = run_once(store, "arkan-worker-01", [])
            task = report["task"]
            self.assertEqual(task["task_id"], created["task_id"])
            self.assertEqual(task["status"], "COMPLETED")
            self.assertEqual(task["proof"]["state"], "ACCEPTED")
            self.assertTrue(task["proof"]["verified"])
            self.assertEqual(task["result"]["worker_id"], "arkan-worker-01")
            self.assertIn("hostname", task["result"]["host"])

    def test_idle_when_queue_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = HomeServerStore(Path(tmp) / "home.sqlite3")
            result = run_once(store, "arkan-worker-01", [])
            self.assertEqual(result["status"], "IDLE")


if __name__ == "__main__":
    unittest.main()
