import unittest
from datetime import datetime, timezone

from brain_v12.brain.brain_cloud_provider import WorkerRecord, brain_provider_inventory


class BrainCloudProviderTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 15, 13, 40, tzinfo=timezone.utc)
        self.worker = WorkerRecord(
            worker_id="worker-1",
            provider_instance_id="instance-1",
            cpu_cores=2,
            memory_gib=4,
            storage_gib=64,
            authenticated=True,
            heartbeat_at="2026-10-15T13:39:30Z",
            physical_or_cloud_backed=True,
            verified_zero_cost=True,
            authorized=True,
        )

    def test_no_worker_means_no_capacity(self):
        result = brain_provider_inventory([], now=self.now)
        self.assertEqual(result["provider"], "brain-cloud")
        self.assertEqual(result["status"], "NO_VERIFIED_CAPACITY")
        self.assertEqual(result["worker_count"], 0)
        self.assertFalse(result["provisioning_supported"])
        self.assertFalse(result["capacity_is_manufactured"])

    def test_accepts_only_real_authorized_fresh_free_worker(self):
        result = brain_provider_inventory([self.worker], now=self.now)
        self.assertEqual(result["status"], "CAPACITY_AVAILABLE")
        self.assertEqual(result["worker_count"], 1)
        self.assertEqual(result["workers"][0]["provider_instance_id"], "instance-1")

    def test_rejects_simulated_or_unverified_worker(self):
        simulated = WorkerRecord(
            **{**self.worker.__dict__, "physical_or_cloud_backed": False}
        )
        result = brain_provider_inventory([simulated], now=self.now)
        self.assertEqual(result["status"], "NO_VERIFIED_CAPACITY")
        self.assertIn("NO_REAL_BACKING_RESOURCE", result["rejected_workers"][0]["reasons"])

    def test_rejects_stale_heartbeat(self):
        stale = WorkerRecord(**{**self.worker.__dict__, "heartbeat_at": "2026-10-15T13:30:00Z"})
        result = brain_provider_inventory([stale], now=self.now)
        self.assertIn("HEARTBEAT_STALE_OR_INVALID", result["rejected_workers"][0]["reasons"])


if __name__ == "__main__":
    unittest.main()
