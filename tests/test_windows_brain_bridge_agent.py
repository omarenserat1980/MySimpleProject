import unittest
from unittest.mock import patch

from tools.windows_brain_bridge_agent import (
    ALLOWED_TASKS, execute, validate_config,
)


class WindowsBridgeAgentTests(unittest.TestCase):
    def test_only_read_only_fixed_tasks_are_allowed(self):
        self.assertEqual(ALLOWED_TASKS, {"status", "platform", "python_version"})
        with self.assertRaisesRegex(ValueError, "TASK_NOT_ALLOWED"):
            execute("powershell")
        with self.assertRaisesRegex(ValueError, "TASK_NOT_ALLOWED"):
            execute("brain_runtime_launch")

    def test_status_labels_observed_host_and_no_reservation(self):
        result = execute("status")
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["execution_scope"], "READ_ONLY")
        self.assertEqual(result["resource_snapshot"]["reality"], "OBSERVED_HOST")
        self.assertEqual(result["resource_snapshot"]["resource_reservation"], "NONE")

    def test_https_required_by_default(self):
        with patch.dict("os.environ", {
            "V12_AGENT_ID": "windows-bridge-test",
            "V12_BRAIN_URL": "http://192.168.1.10:8012",
        }, clear=True):
            with self.assertRaisesRegex(RuntimeError, "HTTPS_REQUIRED"):
                validate_config()

    def test_http_override_must_be_explicit(self):
        with patch.dict("os.environ", {
            "V12_AGENT_ID": "windows-bridge-test",
            "V12_BRAIN_URL": "http://192.168.1.10:8012",
            "BRAIN_ALLOW_INSECURE_HTTP": "1",
        }, clear=True):
            validate_config()

    def test_agent_id_must_be_namespaced(self):
        with patch.dict("os.environ", {
            "V12_AGENT_ID": "redmi3-01",
            "V12_BRAIN_URL": "https://brain.example.invalid",
        }, clear=True):
            with self.assertRaisesRegex(RuntimeError, "V12_AGENT_ID_MUST_START"):
                validate_config()


if __name__ == "__main__":
    unittest.main()
