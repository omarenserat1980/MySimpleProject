import os
import unittest
from brain_v12.brain.device_bridge import DeviceBridge


class DeviceBridgeTests(unittest.TestCase):
    def setUp(self):
        self.old = os.environ.get("V12_AGENT_KEY")
        os.environ["V12_AGENT_KEY"] = "test-device-key"

    def tearDown(self):
        if self.old is None:
            os.environ.pop("V12_AGENT_KEY", None)
        else:
            os.environ["V12_AGENT_KEY"] = self.old

    def test_queue_poll_report(self):
        b = DeviceBridge()
        queued = b.enqueue("status")
        self.assertTrue(queued["ok"])
        task_id = queued["task"]["task_id"]
        polled = b.poll("android-test")
        self.assertTrue(polled["ok"])
        self.assertEqual(polled["task"]["task_id"], task_id)
        reported = b.report(task_id, "android-test", True, {"status": "READY"})
        self.assertTrue(reported["ok"])
        self.assertEqual(reported["status"], "COMPLETED")
        self.assertTrue(b.result(task_id)["ok"])

    def test_rejects_unknown_task(self):
        b = DeviceBridge()
        result = b.enqueue("shell")
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "TASK_NOT_ALLOWED")


if __name__ == "__main__":
    unittest.main()
