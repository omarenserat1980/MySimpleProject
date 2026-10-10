import unittest
from brain_v12.brain.background_work_coordinator import BackgroundWorkCoordinator

class TestBackgroundWorkCoordinator(unittest.TestCase):
    def setUp(self):
        self.coordinator = BackgroundWorkCoordinator(max_workers=2, max_pending=8)

    def tearDown(self):
        self.coordinator.shutdown(wait=True)

    def test_allowlisted_simulation_job_completes(self):
        submitted = self.coordinator.submit("simulation_health")
        self.assertTrue(submitted["ok"])
        job_id = submitted["job"]["job_id"]
        future = self.coordinator._futures[job_id]
        future.result(timeout=3)
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

if __name__ == "__main__":
    unittest.main(verbosity=2)
