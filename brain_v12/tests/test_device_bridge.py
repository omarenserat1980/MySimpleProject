import os
import tempfile
import unittest
from brain_v12.brain.device_bridge import DeviceBridge
from brain_v12.brain.memory import MemoryStore


class DeviceBridgeTests(unittest.TestCase):
    def setUp(self):
        self.env_keys = ("TERMUX_AGENT_KEY", "BRAIN_AGENT_KEY", "BRAIN_AGENT_KEY_SHA256", "BRAIN_EMULATOR_KEY", "BRAIN_EMULATOR_AGENT_KEY", "BRAIN_AGENT_KEY_FILE", "V12_AGENT_KEY_FILE")
        self.old_env = {k: os.environ.get(k) for k in self.env_keys}
        for key in self.env_keys:
            os.environ.pop(key, None)
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

    def test_heartbeat_registers_software_worker_without_hardware_claims(self):
        agent_id = "software-executor-redmi3-01"
        response = self.bridge.heartbeat(agent_id, {"node_type": "software", "runtime": "termux", "agent": "V12-Termux-Agent"})
        self.assertEqual(response["status"], "HEARTBEAT")
        self.assertEqual(response["agent_id"], agent_id)
        self.assertEqual(response["metadata"]["node_type"], "software")
        self.assertNotIn("cpu_cores", response["metadata"])
        self.assertNotIn("memory_mb", response["metadata"])
        status = self.bridge.agent_status()
        self.assertTrue(status["online"])
        self.assertEqual(status["agents"][0]["agent_id"], agent_id)

    def test_unknown_android_capability_task_is_rejected_before_queueing(self):
        queued = self.bridge.enqueue("internet_download", {"url": "https://example.invalid"})
        self.assertFalse(queued["ok"])
        self.assertEqual(queued["status"], "TASK_NOT_ALLOWED")
        polled = self.bridge.poll("software-executor-redmi3-01")
        self.assertEqual(polled["status"], "IDLE")
        self.assertIsNone(polled["task"])

    def test_rejects_unknown_task(self):
        result = self.bridge.enqueue("shell")
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "TASK_NOT_ALLOWED")

    def test_requeues_stale_claim(self):
        result = self.bridge.requeue_stale(5)
        self.assertEqual(result["requeued"], 0)


if __name__ == "__main__":
    unittest.main()
