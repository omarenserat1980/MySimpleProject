import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from brain_v12.brain import arkan_software_executor_api as api
from brain_v12.brain.arkan_software_executor import ArkanSoftwareExecutor


class ArkanSoftwareExecutorApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.executor = ArkanSoftwareExecutor(Path(self.temp.name) / "node")
        self.old_executor = api._executor
        api._executor = self.executor
        self.auth = patch.object(api, "require_control_key")
        self.auth.start()

    def tearDown(self):
        self.auth.stop()
        api._executor = self.old_executor
        self.executor.close()
        self.temp.cleanup()

    def test_submit_status_and_task_lookup(self):
        result = api.submit_software_task(None, {
            "task_type": "cpu_smoke", "idempotency_key": "api-smoke-1",
        })
        self.assertTrue(result["ok"])
        task_id = result["submission"]["task_id"]
        deadline = time.time() + 5
        task = api.get_software_task(task_id, None)
        while task["task"]["status"] not in {"COMPLETED", "FAILED"} and time.time() < deadline:
            time.sleep(0.01)
            task = api.get_software_task(task_id, None)
        self.assertEqual(task["task"]["status"], "COMPLETED")
        self.assertEqual(task["task"]["reality"], "SIMULATED")
        status = api.software_executor_status(None)
        self.assertEqual(status["node"]["id"], "arkan-virtual-01")
        self.assertEqual(status["runtime_mode"], "PROCESS_LOCAL")

    def test_api_rejects_unapproved_task_type(self):
        with self.assertRaises(HTTPException) as error:
            api.submit_software_task(None, {"task_type": "shell"})
        self.assertEqual(error.exception.status_code, 422)
        self.assertEqual(error.exception.detail["code"], "TASK_TYPE_NOT_ALLOWED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
