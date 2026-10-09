import os
import tempfile
import unittest
from brain_v12.brain.device_bridge import DeviceBridge
from brain_v12.brain.memory import MemoryStore


class DeviceBridgeTests(unittest.TestCase):
    ENV_KEYS = (
        "TERMUX_AGENT_KEY",
        "BRAIN_AGENT_KEY",
        "BRAIN_AGENT_KEY_SHA256",
        "BRAIN_EMULATOR_KEY",
        "BRAIN_EMULATOR_AGENT_KEY",
        "BRAIN_AGENT_KEY_FILE",
        "V12_AGENT_KEY_FILE",
    )

    def setUp(self):
        self.old_env = {key: os.environ.get(key) for key in self.ENV_KEYS}
        for key in self.ENV_KEYS:
            os.environ.pop(key, None)
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

    def test_authentication_fails_closed_without_configured_key(self):
        self.assertFalse(self.bridge.configured())
        self.assertFalse(self.bridge.authenticate("any-key"))
        self.assertEqual(self.bridge.auth_mode(), "NOT_CONFIGURED")

    def test_authentication_accepts_existing_legacy_termux_key_alias(self):
        os.environ["TERMUX_AGENT_KEY"] = "existing-test-key"
        self.assertTrue(self.bridge.configured())
        self.assertEqual(self.bridge.auth_mode(), "LEGACY_TERMUX_AGENT_KEY")
        self.assertTrue(self.bridge.authenticate("existing-test-key"))
        self.assertFalse(self.bridge.authenticate("wrong-key"))

    def test_canonical_key_takes_precedence_over_legacy_alias(self):
        os.environ["BRAIN_AGENT_KEY"] = "canonical-key"
        os.environ["TERMUX_AGENT_KEY"] = "legacy-key"
        self.assertEqual(self.bridge.auth_mode(), "DIRECT_KEY")
        self.assertTrue(self.bridge.authenticate("canonical-key"))
        self.assertFalse(self.bridge.authenticate("legacy-key"))

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
