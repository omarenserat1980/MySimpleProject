import unittest
from unittest.mock import patch

import tools.windows_brain_bridge_agent as bridge
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

    def test_valid_https_endpoint_with_allowlist(self):
        with patch.dict("os.environ", {
            "V12_AGENT_ID": "windows-bridge-test",
            "V12_BRAIN_URL": "https://brain.example.invalid",
            "V12_BRAIN_ALLOWED_HOSTS": "brain.example.invalid",
            "V12_AGENT_KEY_FILE": "/tmp/windows-bridge-test.key",
            "V12_POLL_SECONDS": "17",
        }, clear=True):
            validate_config()
            self.assertEqual(bridge.AGENT_ID, "windows-bridge-test")
            self.assertEqual(bridge.BRAIN_URL, "https://brain.example.invalid")
            self.assertEqual(str(bridge.KEY_FILE), "/tmp/windows-bridge-test.key")
            self.assertEqual(bridge.POLL_SECONDS, 17.0)

    def test_http_override_must_be_explicit(self):
        with patch.dict("os.environ", {
            "V12_AGENT_ID": "windows-bridge-test",
            "V12_BRAIN_URL": "http://192.168.1.10:8012",
            "V12_BRAIN_ALLOWED_HOSTS": "192.168.1.10",
            "BRAIN_ALLOW_INSECURE_HTTP": "1",
        }, clear=True):
            validate_config()

    def test_rejects_url_credentials_query_and_fragment(self):
        for url in (
            "https://user:secret@brain.example.invalid",
            "https://brain.example.invalid?token=oops",
            "https://brain.example.invalid#fragment",
            "https://brain.example.invalid/api",
        ):
            with self.subTest(url=url), patch.dict("os.environ", {
                "V12_AGENT_ID": "windows-bridge-test",
                "V12_BRAIN_URL": url,
            }, clear=True):
                with self.assertRaisesRegex(RuntimeError, "INVALID_BRAIN_URL"):
                    validate_config()

    def test_host_allowlist_is_required(self):
        with patch.dict("os.environ", {
            "V12_AGENT_ID": "windows-bridge-test",
            "V12_BRAIN_URL": "https://brain.example.invalid",
        }, clear=True):
            with self.assertRaisesRegex(RuntimeError, "V12_BRAIN_ALLOWED_HOSTS_REQUIRED"):
                validate_config()

    def test_host_allowlist_blocks_unapproved_host(self):
        with patch.dict("os.environ", {
            "V12_AGENT_ID": "windows-bridge-test",
            "V12_BRAIN_URL": "https://unexpected.example.invalid",
            "V12_BRAIN_ALLOWED_HOSTS": "brain.example.invalid",
        }, clear=True):
            with self.assertRaisesRegex(RuntimeError, "BRAIN_HOST_NOT_ALLOWLISTED"):
                validate_config()

    def test_agent_id_must_be_namespaced(self):
        with patch.dict("os.environ", {
            "V12_AGENT_ID": "redmi3-01",
            "V12_BRAIN_URL": "https://brain.example.invalid",
            "V12_BRAIN_ALLOWED_HOSTS": "brain.example.invalid",
        }, clear=True):
            with self.assertRaisesRegex(RuntimeError, "V12_AGENT_ID_MUST_START"):
                validate_config()


    def test_invalid_poll_interval_fails_closed_without_partial_config_update(self):
        for poll_value in ("not-a-number", "nan", "inf", "-inf"):
            with self.subTest(poll_value=poll_value), patch.dict("os.environ", {
                "V12_AGENT_ID": "windows-bridge-invalid-poll",
                "V12_BRAIN_URL": "https://brain.example.invalid",
                "V12_BRAIN_ALLOWED_HOSTS": "brain.example.invalid",
                "V12_POLL_SECONDS": poll_value,
            }, clear=True), patch.object(bridge, "AGENT_ID", "stable-agent-id"), patch.object(
                bridge, "BRAIN_URL", "https://stable.example.invalid"
            ), patch.object(bridge, "POLL_SECONDS", 23.0):
                with self.assertRaisesRegex(RuntimeError, "INVALID_V12_POLL_SECONDS"):
                    validate_config()
                self.assertEqual(bridge.AGENT_ID, "stable-agent-id")
                self.assertEqual(bridge.BRAIN_URL, "https://stable.example.invalid")
                self.assertEqual(bridge.POLL_SECONDS, 23.0)



if __name__ == "__main__":
    unittest.main()
