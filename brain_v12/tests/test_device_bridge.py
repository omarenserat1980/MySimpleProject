import json
import os
import tempfile
import unittest
from brain_v12.brain.device_bridge import DeviceBridge
from brain_v12.brain.memory import MemoryStore


class DeviceBridgeTests(unittest.TestCase):
    def setUp(self):
        self.env_keys = (
            "TERMUX_AGENT_KEY",
            "BRAIN_AGENT_KEY",
            "BRAIN_AGENT_KEY_SHA256",
            "BRAIN_AGENT_KEYS_JSON",
            "BRAIN_EMULATOR_KEY",
        )
        self.old_env = {key: os.environ.get(key) for key in self.env_keys}
        for key in self.env_keys:
            os.environ.pop(key, None)
        # The bridge uses BRAIN_AGENT_KEY as its local trust root.
        # TERMUX_AGENT_KEY is a legacy variable and must not enable the bridge.
        os.environ["BRAIN_AGENT_KEY"] = "test-device-key"
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
        self.assertTrue(self.bridge.configured())
        self.assertTrue(self.bridge.authenticate("test-device-key"))
        self.assertFalse(self.bridge.authenticate("wrong-key"))

    def test_per_agent_keys_are_isolated_and_fail_closed(self):
        os.environ["BRAIN_AGENT_KEYS_JSON"] = json.dumps({
            "redmi3-01": "redmi-secret-test",
            "realme-01": "realme-secret-test",
        })
        self.assertEqual(self.bridge.auth_mode(), "PER_AGENT_KEYS_JSON")
        self.assertTrue(self.bridge.authenticate("redmi-secret-test", "redmi3-01"))
        self.assertTrue(self.bridge.authenticate("realme-secret-test", "realme-01"))
        self.assertFalse(self.bridge.authenticate("realme-secret-test", "redmi3-01"))
        self.assertFalse(self.bridge.authenticate("realme-secret-test", "unknown-agent"))
        self.assertFalse(self.bridge.authenticate("test-device-key", "redmi3-01"))

    def test_per_agent_registry_rejects_duplicate_credentials(self):
        os.environ["BRAIN_AGENT_KEYS_JSON"] = json.dumps({
            "redmi3-01": "same-secret",
            "realme-01": "same-secret",
        })
        self.assertFalse(self.bridge.authenticate("same-secret", "redmi3-01"))

    def test_queue_poll_report(self):
        queued = self.bridge.enqueue("status")
        self.assertTrue(queued["ok"])
        self.assertEqual(queued["status"], "QUEUED")
        task = queued["task"]
        polled = self.bridge.poll("android-test")
        self.assertTrue(polled["ok"])
        self.assertEqual(polled["status"], "TASK_AVAILABLE")
        self.assertEqual(polled["task"]["task_id"], task["task_id"])
        reported = self.bridge.report(
            task["task_id"], "android-test", True, {"status": "READY"}
        )
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
