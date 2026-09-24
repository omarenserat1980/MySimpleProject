import os
import tempfile
import unittest
from brain_v12.brain.device_bridge import DeviceBridge
from brain_v12.brain.memory import MemoryStore


class DeviceBridgeTests(unittest.TestCase):
    def setUp(self):
        self.old = os.environ.get("V12_AGENT_KEY")
        os.environ["V12_AGENT_KEY"] = "test-device-key"
        self.tmp = tempfile.NamedTemporaryFile(delete=False)
        self.tmp.close()
        self.store = MemoryStore(self.tmp.name)
        self.store.init()
        self.bridge = DeviceBridge(self.store)

    def tearDown(self):
        if self.old is None:
            os.environ.pop("V12_AGENT_KEY", None)
        else:
            os.environ["V12_AGENT_KEY"] = self.old
        try:
            os.unlink(self.tmp.name)
        except FileNotFoundError:
            pass

    def test_queue_poll_report(self):
        queued = self.bridge.enqueue("status")
        self.assertTrue(queued["ok"])
        task_id = queued["task"]["task_id"]
        polled = self.bridge.poll("android-test")
        self.assertTrue(polled["ok"])
        self.assertEqual(polled["task"]["task_id"], task_id)
        reported = self.bridge.report(task_id, "android-test", True, {"status": "READY"})
        self.assertTrue(reported["ok"])
        self.assertEqual(reported["status"], "COMPLETED")
        self.assertTrue(self.bridge.result(task_id)["ok"])

    def test_rejects_unknown_task(self):
        result = self.bridge.enqueue("shell")
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "TASK_NOT_ALLOWED")


if __name__ == "__main__":
    unittest.main()
