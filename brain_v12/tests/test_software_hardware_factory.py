import unittest
from types import SimpleNamespace
from unittest.mock import patch

from brain_v12.brain.software_hardware_factory import SoftwareHardwareFactory


def fake_host():
    return SimpleNamespace(
        node_id="brain-test-host",
        platform="linux",
        cpu_cores=8.0,
        memory_mb=8192,
        disk_mb=20000,
        source="local_host_measurement",
        observed=True,
    )


class SoftwareHardwareFactoryTests(unittest.TestCase):
    def setUp(self):
        self.patch = patch(
            "brain_v12.brain.software_hardware_factory.local_host_node",
            side_effect=fake_host,
        )
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.factory = SoftwareHardwareFactory()

    def test_status_distinguishes_logical_budget_from_physical_resources(self):
        status = self.factory.status()
        self.assertEqual(status["execution_host"], "brain-test-host")
        self.assertEqual(status["capacity"]["cpu_cores_physical_observed"], 8.0)
        self.assertEqual(status["capacity"]["cpu_cores_logical_budget"], 4.0)
        self.assertIn("not additional physical hardware", status["resource_semantics"])
        self.assertFalse(status["remote_execution_proven"])

    def test_allocate_run_real_bounded_probe_and_release(self):
        allocation = self.factory.allocate(
            task_id="hardware-probe-test",
            cpu_cores=0.25,
            memory_mb=128,
            disk_mb=0,
        )
        lease_id = allocation["lease"]["lease_id"]
        result = self.factory.run_self_test(lease_id, rounds=50)
        job = result["job"]
        self.assertEqual(job["status"], "SUCCEEDED")
        self.assertEqual(job["execution_location"], "brain_host_process")
        self.assertEqual(len(job["result_sha256"]), 64)
        self.assertGreaterEqual(job["duration_seconds"], 0)
        released = self.factory.release(lease_id)
        self.assertEqual(released["lease"]["status"], "RELEASED")
        self.assertEqual(self.factory.status()["allocated"]["active_leases"], 0)

    def test_capacity_overcommit_is_rejected(self):
        self.factory.allocate(
            task_id="first", cpu_cores=3.0, memory_mb=1000, disk_mb=100
        )
        with self.assertRaisesRegex(ValueError, "BLOCKED_INSUFFICIENT_LOGICAL_CAPACITY"):
            self.factory.allocate(
                task_id="second", cpu_cores=2.0, memory_mb=1000, disk_mb=100
            )

    def test_probe_requires_active_lease(self):
        allocation = self.factory.allocate(
            task_id="probe", cpu_cores=0.25, memory_mb=128, disk_mb=0
        )
        lease_id = allocation["lease"]["lease_id"]
        self.factory.release(lease_id)
        with self.assertRaisesRegex(ValueError, "ACTIVE_LEASE_REQUIRED"):
            self.factory.run_self_test(lease_id, rounds=10)

    def test_probe_rounds_are_bounded(self):
        allocation = self.factory.allocate(
            task_id="bounded", cpu_cores=0.25, memory_mb=128, disk_mb=0
        )
        with self.assertRaisesRegex(ValueError, "rounds must be between"):
            self.factory.run_self_test(allocation["lease"]["lease_id"], rounds=100001)


if __name__ == "__main__":
    unittest.main()
