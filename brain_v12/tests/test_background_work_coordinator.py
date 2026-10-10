import sqlite3
import tempfile
import unittest
from pathlib import Path
from brain_v12.brain.background_work_coordinator import BackgroundWorkCoordinator

class TestBackgroundWorkCoordinator(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "background.sqlite3"
        self.coordinator = BackgroundWorkCoordinator(max_workers=2, max_pending=8, db_path=self.db)

    def tearDown(self):
        self.coordinator.shutdown(wait=True)
        self.tmp.cleanup()

    def test_allowlisted_simulation_job_completes(self):
        submitted = self.coordinator.submit("simulation_health")
        self.assertTrue(submitted["ok"])
        job_id = submitted["job"]["job_id"]
        self.coordinator._futures[job_id].result(timeout=3)
        job = self.coordinator.get(job_id)
        self.assertEqual(job["state"], "COMPLETED")
        self.assertEqual(job["reality"], "SIMULATED")
        self.assertTrue(job["result"]["healthy"])

    def test_arbitrary_job_is_rejected(self):
        result = self.coordinator.submit("run_shell_command")
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "BACKGROUND_JOB_NOT_ALLOWLISTED")

    def test_idempotency_key_does_not_duplicate_job(self):
        first = self.coordinator.submit("simulation_inventory", idempotency_key="same-request")
        second = self.coordinator.submit("simulation_inventory", idempotency_key="same-request")
        self.assertEqual(first["job"]["job_id"], second["job"]["job_id"])
        self.assertEqual(second["status"], "DUPLICATE_RETURNED_EXISTING")

    def test_snapshot_marks_simulated_and_bounds_workers(self):
        snapshot = self.coordinator.snapshot()
        self.assertEqual(snapshot["reality"], "SIMULATED")
        self.assertLessEqual(snapshot["max_workers"], 8)
        self.assertEqual(snapshot["policy"], "SIMULATION_FIRST")

    def test_completed_result_survives_restart(self):
        submitted = self.coordinator.submit("simulation_readiness", idempotency_key="persist-me")
        job_id = submitted["job"]["job_id"]
        self.coordinator._futures[job_id].result(timeout=3)
        expected = self.coordinator.get(job_id)
        self.coordinator.shutdown(wait=True)
        self.coordinator = BackgroundWorkCoordinator(max_workers=1, db_path=self.db)
        restored = self.coordinator.get(job_id)
        self.assertEqual(restored["state"], "COMPLETED")
        self.assertEqual(restored["result"], expected["result"])
        duplicate = self.coordinator.submit("simulation_readiness", idempotency_key="persist-me")
        self.assertEqual(duplicate["job"]["job_id"], job_id)

    def test_interrupted_running_job_is_recovered(self):
        self.coordinator.shutdown(wait=True)
        with sqlite3.connect(self.db) as db:
            db.execute("INSERT INTO background_jobs(job_id,kind,state,reality,created_at) VALUES(?,?,?,?,?)",
                       ("interrupted", "simulation_health", "RUNNING", "SIMULATED", 1.0))
        self.coordinator = BackgroundWorkCoordinator(max_workers=1, db_path=self.db)
        future = self.coordinator._futures["interrupted"]
        future.result(timeout=3)
        self.assertEqual(self.coordinator.get("interrupted")["state"], "COMPLETED")

if __name__ == "__main__":
    unittest.main(verbosity=2)
