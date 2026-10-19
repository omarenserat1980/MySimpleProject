import json
import os
import tempfile
import unittest
from unittest.mock import patch
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
            "BRAIN_EMULATOR_AGENT_KEY",
            "BRAIN_ENABLE_DEVICE_BRIDGE",
            "BRAIN_AGENT_KEY_FILE",
            "V12_AGENT_KEY_FILE",
        )
        self.old_env = {key: os.environ.get(key) for key in self.env_keys}
        for key in self.env_keys:
            os.environ.pop(key, None)
        # The bridge uses BRAIN_AGENT_KEY as its local trust root.
        # TERMUX_AGENT_KEY is a legacy variable and must not enable the bridge.
        self.tmp = tempfile.NamedTemporaryFile(delete=False)
        self.tmp.close()
        # Isolate key-file lookup from any real operator credential on this host.
        os.environ["BRAIN_AGENT_KEY_FILE"] = self.tmp.name + ".missing-key"
        os.environ["BRAIN_AGENT_KEY"] = "test-device-key"
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

    def test_runtime_ready_is_independent_of_credentials_and_device_presence(self):
        for key in (
            "BRAIN_AGENT_KEY",
            "BRAIN_AGENT_KEY_SHA256",
            "BRAIN_AGENT_KEYS_JSON",
            "BRAIN_EMULATOR_KEY",
            "BRAIN_EMULATOR_AGENT_KEY",
        ):
            os.environ.pop(key, None)

        status = self.bridge.status()
        self.assertTrue(self.bridge.enabled())
        self.assertTrue(status["configured"])
        self.assertTrue(status["runtime_ready"])
        self.assertTrue(status["enabled"])
        self.assertFalse(status["auth_configured"])
        self.assertFalse(status["agents"]["online"])
        self.assertEqual(self.bridge.enqueue("status")["status"], "AUTH_NOT_CONFIGURED")

    def test_robot_memory_is_returned_to_agent_and_persists_reported_results(self):
        self.store.record_robot_task_result(
            "redmi3-01", "prior-task", "python_version", True,
            {"stdout": "Python 3.13.13", "returncode": 0},
        )
        self.store.device_task_create("memory-task", "brain_memory_context", {}, 1)
        claimed = self.bridge.poll("redmi3-01")
        self.assertEqual(claimed["task"]["task_id"], "memory-task")
        history = claimed["task"]["params"]["brain_memory_context"]["history"]
        self.assertEqual(history[-1]["task_id"], "prior-task")
        self.assertNotIn("stdout", history[-1]["result"])

        report = self.bridge.report(
            "memory-task", "redmi3-01", True,
            {"status": "MEMORY_CONTEXT_RECEIVED", "history_count": len(history)},
        )
        self.assertEqual(report["status"], "COMPLETED")
        persisted = self.store.robot_memory_context("redmi3-01")["history"]
        self.assertEqual(persisted[-1]["task_id"], "memory-task")
        self.assertEqual(persisted[-1]["result"]["status"], "MEMORY_CONTEXT_RECEIVED")

    def test_runtime_switch_can_disable_bridge_without_credentials(self):
        for key in (
            "BRAIN_AGENT_KEY",
            "BRAIN_AGENT_KEY_SHA256",
            "BRAIN_AGENT_KEYS_JSON",
            "BRAIN_EMULATOR_KEY",
            "BRAIN_EMULATOR_AGENT_KEY",
        ):
            os.environ.pop(key, None)
        os.environ["BRAIN_ENABLE_DEVICE_BRIDGE"] = "0"

        status = self.bridge.status()
        self.assertTrue(status["runtime_ready"])
        self.assertFalse(status["enabled"])
        self.assertFalse(status["auth_configured"])
        self.assertEqual(self.bridge.enqueue("status")["status"], "BRIDGE_DISABLED")

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


    def test_key_authentication_and_heartbeat_liveness_are_separate_checks(self):
        agent_id = "redmi3-01"
        self.assertTrue(self.bridge.authenticate("test-device-key", agent_id))

        heartbeat = self.bridge.heartbeat(agent_id, {
            "source": "termux-agent",
            "reality": "TEST_FIXTURE",
            "test_run_id": "heartbeat-proof-test",
        })
        self.assertTrue(heartbeat["ok"])
        self.assertEqual(heartbeat["status"], "HEARTBEAT")

        status = self.bridge.agent_status()
        record = next(item for item in status["agents"] if item["agent_id"] == agent_id)
        self.assertTrue(record["online"])
        self.assertEqual(record["state"], "ONLINE")
        self.assertLessEqual(record["age_seconds"], status["ttl_seconds"])

    def test_wrong_agent_key_does_not_authorize_heartbeat_claim(self):
        os.environ["BRAIN_AGENT_KEYS_JSON"] = json.dumps({
            "redmi3-01": "redmi-secret-test",
            "realme-01": "realme-secret-test",
        })
        self.assertFalse(self.bridge.authenticate("realme-secret-test", "redmi3-01"))
        self.assertFalse(self.bridge.authenticate("wrong-key", "redmi3-01"))

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

    def test_capability_task_requires_online_android_executor(self):
        result = self.bridge.enqueue(
            "internet_download", {"url": "https://example.invalid"}
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "CAPABILITY_WORKER_OFFLINE")
        self.assertEqual(result["required_executor"], "android-executor-*")

    def test_non_android_worker_cannot_claim_android_capability_tasks(self):
        # Synthetic heartbeats exercise routing only; no physical device is contacted.
        self.bridge.heartbeat(
            "software-executor-redmi3-01",
            {"node_type": "software", "runtime": "termux"},
        )
        self.bridge.heartbeat(
            "android-executor-test",
            {"node_type": "android_executor", "runtime": "test"},
        )
        queued = self.bridge.enqueue(
            "internet_download", {"url": "https://example.invalid"}
        )
        self.assertTrue(queued["ok"])
        software_poll = self.bridge.poll("software-executor-redmi3-01")
        self.assertEqual(software_poll["status"], "IDLE")
        self.assertIsNone(software_poll["task"])
        android_poll = self.bridge.poll("android-executor-test")
        self.assertEqual(android_poll["status"], "TASK_AVAILABLE")
        self.assertEqual(android_poll["task"]["task"], "internet_download")

    def test_rejects_unknown_task(self):
        result = self.bridge.enqueue("shell")
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "TASK_NOT_ALLOWED")

    def test_audit_tasks_are_allowlisted_and_report_diagnostic_completion(self):
        for task_name in ("brain_project_audit", "windows_cloud_boot_preflight"):
            with self.subTest(task=task_name):
                queued = self.bridge.enqueue(task_name)
                self.assertTrue(queued["ok"])
                task = queued["task"]
                polled = self.bridge.poll("brain-emulator-test")
                self.assertEqual(polled["task"]["task"], task_name)
                report = {
                    "returncode": 2,
                    "status": "BLOCKED",
                    "boot_path": {"blockers": ["KVM_UNAVAILABLE_OR_PERMISSION_DENIED"]},
                    "project_areas": {"brain_v12/brain": {"exists": True}},
                }
                self.assertTrue(self.bridge.report(task["task_id"], "brain-emulator-test", True, report)["ok"])
                verified = self.bridge.verify_result(task["task_id"])
                self.assertTrue(verified["verified"])
                self.assertEqual(verified["status"], "VERIFIED")

    def test_requeues_stale_claim(self):
        result = self.bridge.requeue_stale(5)
        self.assertEqual(result["requeued"], 0)


    def test_heartbeat_expires_after_ttl(self):
        os.environ["TERMUX_AGENT_TTL_SECONDS"] = "10"
        with patch("brain_v12.brain.device_bridge.time.time", return_value=1000.0):
            self.bridge.heartbeat("realme-test", {"reality": "TEST_FIXTURE"})
        with patch("brain_v12.brain.device_bridge.time.time", return_value=1011.0):
            status = self.bridge.agent_status()
        record = next(item for item in status["agents"] if item["agent_id"] == "realme-test")
        self.assertFalse(record["online"])
        self.assertEqual(record["state"], "STALE")
        self.assertEqual(record["age_seconds"], 11.0)
        self.assertFalse(status["online"])
        os.environ.pop("TERMUX_AGENT_TTL_SECONDS", None)

    def test_heartbeat_is_online_at_ttl_boundary(self):
        os.environ["TERMUX_AGENT_TTL_SECONDS"] = "10"
        with patch("brain_v12.brain.device_bridge.time.time", return_value=1000.0):
            self.bridge.heartbeat("realme-boundary-test", {"reality": "TEST_FIXTURE"})
        with patch("brain_v12.brain.device_bridge.time.time", return_value=1010.0):
            status = self.bridge.agent_status()
        record = next(item for item in status["agents"] if item["agent_id"] == "realme-boundary-test")
        self.assertTrue(record["online"])
        self.assertEqual(record["state"], "ONLINE")
        os.environ.pop("TERMUX_AGENT_TTL_SECONDS", None)


if __name__ == "__main__":
    unittest.main()
