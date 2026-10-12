import json
import tempfile
import time
import unittest
from pathlib import Path

from brain_v12.brain.arkan_software_executor import ArkanSoftwareExecutor
from brain_v12.brain.durable_task_store import DurableTaskStore


class ArkanSoftwareExecutorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "node"

    def tearDown(self):
        self.temp.cleanup()

    def wait_for_terminal(self, service, task_id, timeout=5.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            result = service.task_status(task_id)
            task = result.get("task", {})
            if task.get("status") in {"COMPLETED", "FAILED"}:
                return task
            time.sleep(0.01)
        self.fail(f"task did not finish: {service.task_status(task_id)}")

    def test_predefined_workload_completes_and_survives_service_restart(self):
        service = ArkanSoftwareExecutor(self.root)
        submitted = service.submit("cpu_smoke", idempotency_key="acceptance-cpu-smoke")
        task = self.wait_for_terminal(service, submitted["task_id"])
        self.assertEqual(task["status"], "COMPLETED")
        self.assertEqual(task["reality"], "SIMULATED")
        self.assertEqual(task["result"]["result"]["output"], [2025])
        service.close()

        restarted = ArkanSoftwareExecutor(self.root)
        try:
            recovered = restarted.task_status(submitted["task_id"])["task"]
            self.assertEqual(recovered["status"], "COMPLETED")
            self.assertEqual(recovered["result"]["result"]["output"], [2025])
            snapshot = restarted.status()
            self.assertEqual(snapshot["node"]["id"], "arkan-virtual-01")
            self.assertEqual(snapshot["runtime_mode"], "PROCESS_LOCAL")
            self.assertFalse(snapshot["physical_host_required"])
            self.assertFalse(snapshot["windows_server_2025"]["native_os_boot_verified"])
            persisted = json.loads((self.root / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(persisted["reality"], "SIMULATED")
        finally:
            restarted.close()

    def test_unsupported_task_type_is_rejected(self):
        service = ArkanSoftwareExecutor(self.root)
        try:
            with self.assertRaisesRegex(ValueError, "TASK_TYPE_NOT_ALLOWED"):
                service.submit("arbitrary_shell", idempotency_key="must-not-run")
            self.assertEqual(service.queue.status()["tasks"], 0)
        finally:
            service.close()

    def test_interrupted_running_task_is_recovered_after_restart(self):
        self.root.mkdir(parents=True)
        store = DurableTaskStore(self.root / "tasks.sqlite3")
        payload = {
            "program": [["MOVI", 0, 2025], ["OUT", 0], ["HALT"]],
            "required_capabilities": ["cpu"],
            "requirement": {},
            "priority": "NORMAL",
        }
        row = store.submit("interrupted-task", payload, "recover-after-crash")
        claimed = store.claim(row["task_id"], "lost-process-worker", 300)
        self.assertIsNotNone(claimed)
        self.assertEqual(claimed["status"], "RUNNING")
        store.close()

        service = ArkanSoftwareExecutor(self.root)
        try:
            task = self.wait_for_terminal(service, "interrupted-task")
            self.assertEqual(task["status"], "COMPLETED")
            self.assertGreaterEqual(task["attempt"], 2)
            self.assertEqual(task["result"]["result"]["output"], [2025])
        finally:
            service.close()

    def test_idempotency_key_returns_original_task(self):
        service = ArkanSoftwareExecutor(self.root)
        try:
            first = service.submit("cpu_smoke", idempotency_key="same-request")
            second = service.submit("cpu_smoke", idempotency_key="same-request")
            self.assertEqual(first["task_id"], second["task_id"])
        finally:
            service.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
