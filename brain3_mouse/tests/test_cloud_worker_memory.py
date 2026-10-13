from __future__ import annotations

import unittest

from brain3_mouse.cloud_worker_memory import CloudWorkerMemoryBridge
from brain3_mouse.unified_kernel import UnifiedBrainKernel


class CloudWorkerMemoryBridgeTests(unittest.TestCase):
    def setUp(self):
        self.kernel = UnifiedBrainKernel()
        self.worker = CloudWorkerMemoryBridge(self.kernel, "cloud-worker-01")

    def test_worker_reads_brain_owned_context_from_shared_ledger(self):
        self.kernel.memory_set("brain:context:project", {"name": "Brain 3"})
        self.assertEqual(
            self.worker.read_context(),
            {"brain:context:project": {"name": "Brain 3"}},
        )

    def test_worker_cannot_read_other_worker_memory_namespaces(self):
        self.kernel.memory_set("cloud_worker:cloud-worker-02:evidence:1", {"secret": "not shared"})
        with self.assertRaises(PermissionError):
            self.worker.read_context(prefix="cloud_worker:")

    def test_safe_worker_task_enters_brains_shared_queue(self):
        task = self.worker.submit_task("inspect", "inspect a proposed change")
        self.assertEqual(task["queue"], "brain3_shared")
        self.assertEqual(task["requested_by"], "cloud_worker:cloud-worker-01")
        self.assertFalse(task["executed"])
        self.assertEqual(
            self.kernel.memory_get("cloud_worker:cloud-worker-01:task:1")["state"],
            "QUEUED",
        )

    def test_worker_evidence_is_written_to_shared_brain_memory(self):
        task = self.worker.submit_task("test", "run a contract test")
        record = self.worker.record_result(task["id"], "completed", {"test": "passed"})
        self.assertEqual(self.kernel.memory_get(
            "cloud_worker:cloud-worker-01:evidence:1"
        ), record)
        self.assertFalse(record["verified_by_brain"])
        self.assertFalse(record["cloud_connected"])
        self.assertFalse(record["windows_boot_verified"])
        self.assertEqual(self.worker.evidence_for(task["id"]), record)

    def test_worker_cannot_self_verify_or_report_for_other_worker(self):
        task = self.worker.submit_task("inspect", "inspect")
        with self.assertRaises(PermissionError):
            self.worker.record_result(task["id"], "completed", {}, verified=True)
        other = CloudWorkerMemoryBridge(self.kernel, "cloud-worker-02")
        with self.assertRaises(PermissionError):
            other.record_result(task["id"], "completed", {})

    def test_worker_cannot_submit_blocked_actions_or_impersonate_sources(self):
        with self.assertRaises(PermissionError):
            self.worker.submit_task("windows_boot", "boot Windows")
        with self.assertRaises(PermissionError):
            self.worker.submit_task("inspect", "inspect", requested_by="legacy_brain")

    def test_status_does_not_claim_real_cloud_connectivity(self):
        status = self.worker.status()
        self.assertTrue(status["shared_memory"])
        self.assertEqual(status["transport"], "in_process_only")
        self.assertFalse(status["cloud_connected"])
        self.assertFalse(status["authenticated_remote_identity"])
        self.assertFalse(status["production_ready"])

    def test_worker_identifier_is_validated(self):
        with self.assertRaises(ValueError):
            CloudWorkerMemoryBridge(self.kernel, "../other-worker")


if __name__ == "__main__":
    unittest.main()
