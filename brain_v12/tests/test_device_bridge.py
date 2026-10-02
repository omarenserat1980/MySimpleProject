import os
import tempfile
import unittest
from brain_v12.brain.device_bridge import DeviceBridge
from brain_v12.brain.memory import MemoryStore


class DeviceBridgeTests(unittest.TestCase):
    def setUp(self):
        self.old = os.environ.get("TERMUX_AGENT_KEY")
        os.environ["TERMUX_AGENT_KEY"] = "test-device-key"
        self.tmp = tempfile.NamedTemporaryFile(delete=False)
        self.tmp.close()
        self.store = MemoryStore(self.tmp.name)
        self.store.init()
        self.bridge = DeviceBridge(self.store)

    def tearDown(self):
        if self.old is None:
            os.environ.pop("TERMUX_AGENT_KEY", None)
        else:
            os.environ["TERMUX_AGENT_KEY"] = self.old
        try:
            os.unlink(self.tmp.name)
        except FileNotFoundError:
            pass

    def test_authentication(self):
        self.assertFalse(self.bridge.configured())
        self.assertFalse(self.bridge.authenticate("test-device-key"))
        self.assertFalse(self.bridge.authenticate("wrong-key"))

    def test_queue_poll_report(self):
        queued = self.bridge.enqueue("status")
        self.assertTrue(queued["ok"])
        self.assertEqual(queued["status"], "QUEUED")
        task = queued["task"]
        polled = self.bridge.poll("android-test")
        self.assertTrue(polled["ok"])
        self.assertEqual(polled["status"], "TASK_AVAILABLE")
        self.assertEqual(polled["task"]["task_id"], task["task_id"])
        reported = self.bridge.report(task["task_id"], "android-test", True, {"status": "READY"})
        self.assertTrue(reported["ok"])
        self.assertEqual(reported["status"], "COMPLETED")

    def test_rejects_unknown_task(self):
        result = self.bridge.enqueue("shell")
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "TASK_NOT_ALLOWED")

    def test_requeues_stale_claim(self):
        result = self.bridge.requeue_stale(5)
        self.assertEqual(result["requeued"], 0)


if __name__ == "__main__":
    unittest.main()
