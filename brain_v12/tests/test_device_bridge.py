import os
import tempfile
import unittest
from brain_v12.brain.device_bridge import DeviceBridge
from brain_v12.brain.memory import MemoryStore


class DeviceBridgeTests(unittest.TestCase):
    def setUp(self):
        self.env_keys = ("TERMUX_AGENT_KEY", "BRAIN_AGENT_KEY", "BRAIN_AGENT_KEY_SHA256", "BRAIN_EMULATOR_KEY", "BRAIN_AGENT_KEY_FILE", "BRAIN_ENABLE_DEVICE_BRIDGE")
        self.old_env = {k: os.environ.get(k) for k in self.env_keys}
        for key in self.env_keys:
            os.environ.pop(key, None)
        os.environ["TERMUX_AGENT_KEY"] = "test-device-key"
        self.tmp = tempfile.NamedTemporaryFile(delete=False)
        self.tmp.close()
        self.store = MemoryStore(self.tmp.name)
        self.store.init()
        self.bridge = DeviceBridge(self.store)

    def tearDown(self):
        for key, value in self.old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        try:
            os.unlink(self.tmp.name)
        except FileNotFoundError:
            pass

    def test_authentication(self):
        self.assertFalse(self.bridge.configured())
        self.assertFalse(self.bridge.authenticate("test-device-key"))
        self.assertFalse(self.bridge.authenticate("wrong-key"))


    def test_invalid_utf8_key_file_fails_closed_without_crashing(self):
        with tempfile.NamedTemporaryFile(delete=False) as key_file:
            key_file.write(b"\\xff\\xfe\\xfa")
            key_path = key_file.name
        try:
            os.environ["BRAIN_AGENT_KEY_FILE"] = key_path
            for key in ("BRAIN_AGENT_KEY", "BRAIN_AGENT_KEY_SHA256", "BRAIN_EMULATOR_KEY"):
                os.environ.pop(key, None)
            os.environ.pop("BRAIN_ENABLE_DEVICE_BRIDGE", None)
            self.assertFalse(self.bridge.configured())
            self.assertFalse(self.bridge.authenticate("test-device-key"))
        finally:
            os.unlink(key_path)

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
