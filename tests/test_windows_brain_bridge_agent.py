import unittest
from unittest.mock import patch

import tools.windows_brain_bridge_agent as bridge
from tools.windows_brain_bridge_agent import (
    ALLOWED_TASKS, _NoRedirectHandler, execute, validate_config,
)


class WindowsBridgeAgentTests(unittest.TestCase):
    def test_only_read_only_fixed_tasks_are_allowed(self):
        self.assertEqual(ALLOWED_TASKS, {"status", "platform", "python_version"})
        with self.assertRaisesRegex(ValueError, "TASK_NOT_ALLOWED"):
            execute("powershell")
        with self.assertRaisesRegex(ValueError, "TASK_NOT_ALLOWED"):
            execute("brain_runtime_launch")

    def test_redirect_handler_refuses_redirects(self):
        handler = _NoRedirectHandler()
        self.assertIsNone(handler.redirect_request(
            None, None, 302, "Found", {}, "https://unexpected.example.invalid/steal"
        ))

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
            self.assertEqual(bridge.KEY_FILE, bridge.Path("/tmp/windows-bridge-test.key"))
            self.assertEqual(bridge.POLL_SECONDS, 17.0)

    def test_explicit_key_file_does_not_require_home_directory(self):
        with patch.dict("os.environ", {
            "V12_AGENT_ID": "windows-bridge-test",
            "V12_BRAIN_URL": "https://brain.example.invalid",
            "V12_BRAIN_ALLOWED_HOSTS": "brain.example.invalid",
            "V12_AGENT_KEY_FILE": "/tmp/explicit-agent.key",
        }, clear=True), patch.object(
            bridge.Path, "home", side_effect=RuntimeError("home unavailable")
        ):
            validate_config()
            self.assertEqual(bridge.KEY_FILE, bridge.Path("/tmp/explicit-agent.key"))

    def test_http_override_must_be_explicit(self):
        with patch.dict("os.environ", {
            "V12_AGENT_ID": "windows-bridge-test",
            "V12_BRAIN_URL": "http://192.168.1.10:8012",
            "V12_BRAIN_ALLOWED_HOSTS": "192.168.1.10",
            "V12_AGENT_KEY_FILE": "/tmp/windows-bridge-test.key",
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



    def test_run_once_fails_closed_on_malformed_task_payload(self):
        fake_snapshot = {
            "memory": {"available_bytes": None, "total_bytes": None},
            "home_disk": {"free_bytes": 100, "total_bytes": 200},
            "reality": "OBSERVED_HOST",
            "resource_reservation": "NONE",
        }
        malformed_tasks = [
            [],
            {"task_id": "task-1"},
            {"task_id": True, "task": "status"},
            {"task_id": "x" * 201, "task": "status"},
            {"task_id": "task-1", "task": 123},
        ]
        for task in malformed_tasks:
            with self.subTest(task=task), patch.object(
                bridge, "AGENT_ID", "windows-bridge-test"
            ), patch.object(
                bridge, "resource_snapshot", return_value=fake_snapshot
            ), patch.object(
                bridge, "request_json", side_effect=[
                    {"ok": True, "status": "HEARTBEAT", "agent_id": "windows-bridge-test"},
                    {"ok": True, "status": "TASK_AVAILABLE", "task": task},
                ]
            ) as request:
                with self.assertRaisesRegex(RuntimeError, "TASK_(PAYLOAD|ID|NAME)_INVALID"):
                    bridge.run_once("unit-test-key")
                self.assertEqual(request.call_count, 2)

    def test_run_once_rejects_unconfirmed_report(self):
        fake_snapshot = {
            "memory": {"available_bytes": None, "total_bytes": None},
            "home_disk": {"free_bytes": 100, "total_bytes": 200},
            "reality": "OBSERVED_HOST",
            "resource_reservation": "NONE",
        }
        with patch.object(bridge, "AGENT_ID", "windows-bridge-test"), patch.object(
            bridge, "resource_snapshot", return_value=fake_snapshot
        ), patch.object(bridge, "request_json", side_effect=[
            {"ok": True, "status": "HEARTBEAT", "agent_id": "windows-bridge-test"},
            {"ok": True, "status": "TASK_AVAILABLE", "task": {
                "task_id": "test-task-002", "task": "python_version"
            }},
            {"ok": False, "status": "AGENT_MISMATCH", "task": {
                "task_id": "test-task-002"
            }},
        ]):
            with self.assertRaisesRegex(RuntimeError, "REPORT_NOT_CONFIRMED"):
                bridge.run_once("unit-test-key")

    def test_run_once_rejects_unconfirmed_heartbeat(self):
        fake_snapshot = {
            "memory": {"available_bytes": None, "total_bytes": None},
            "home_disk": {"free_bytes": 100, "total_bytes": 200},
            "reality": "OBSERVED_HOST",
            "resource_reservation": "NONE",
        }
        with patch.object(bridge, "AGENT_ID", "windows-bridge-test"), patch.object(
            bridge, "resource_snapshot", return_value=fake_snapshot
        ), patch.object(bridge, "request_json", return_value={
            "ok": False, "status": "UNAUTHORIZED_AGENT"
        }) as request:
            with self.assertRaisesRegex(RuntimeError, "HEARTBEAT_NOT_CONFIRMED"):
                bridge.run_once("unit-test-key")
            self.assertEqual(request.call_count, 1)

    def test_run_once_completes_mocked_heartbeat_poll_report_cycle(self):
        fake_snapshot = {
            "memory": {"available_bytes": 1024 * 1024 * 512, "total_bytes": 1024 * 1024 * 1024},
            "home_disk": {"free_bytes": 1024 * 1024 * 100, "total_bytes": 1024 * 1024 * 500},
            "reality": "OBSERVED_HOST",
            "resource_reservation": "NONE",
        }
        with patch.object(bridge, "AGENT_ID", "windows-bridge-test"), patch.object(
            bridge, "resource_snapshot", return_value=fake_snapshot
        ), patch.object(bridge, "request_json", side_effect=[
            {"ok": True, "status": "HEARTBEAT", "agent_id": "windows-bridge-test"},
            {"ok": True, "status": "TASK_AVAILABLE", "task": {
                "task_id": "test-task-001", "task": "python_version"
            }},
            {"ok": True, "status": "COMPLETED", "task": {"task_id": "test-task-001"}},
        ]) as request:
            result = bridge.run_once("unit-test-key")

        self.assertEqual(result, "REPORTED:python_version")
        self.assertEqual(request.call_count, 3)
        self.assertEqual(request.call_args_list[0].args[:3], (
            "POST", "/api/device/heartbeat", "unit-test-key"
        ))
        self.assertEqual(request.call_args_list[1].args[:3], (
            "GET", "/api/device/poll?agent_id=windows-bridge-test", "unit-test-key"
        ))
        report_call = request.call_args_list[2]
        self.assertEqual(report_call.args[:3], (
            "POST", "/api/device/report", "unit-test-key"
        ))
        self.assertEqual(report_call.args[3]["task_id"], "test-task-001")
        self.assertEqual(report_call.args[3]["agent_id"], "windows-bridge-test")
        self.assertTrue(report_call.args[3]["ok"])
        self.assertIn("python", report_call.args[3]["result"])


    def test_run_once_rejects_poll_task_state_mismatch(self):
        fake_snapshot = {
            "memory": {"available_bytes": None, "total_bytes": None},
            "home_disk": {"free_bytes": 100, "total_bytes": 200},
            "reality": "OBSERVED_HOST",
            "resource_reservation": "NONE",
        }
        with patch.object(bridge, "AGENT_ID", "windows-bridge-test"), patch.object(
            bridge, "resource_snapshot", return_value=fake_snapshot
        ), patch.object(bridge, "request_json", side_effect=[
            {"ok": True, "status": "HEARTBEAT", "agent_id": "windows-bridge-test"},
            {"ok": True, "status": "IDLE", "task": {
                "task_id": "test-task-poll-mismatch", "task": "python_version"
            }},
        ]) as request:
            with self.assertRaisesRegex(RuntimeError, "POLL_TASK_STATE_MISMATCH"):
                bridge.run_once("unit-test-key")
            self.assertEqual(request.call_count, 2)

    def test_run_once_rejects_report_for_different_task_id(self):
        fake_snapshot = {
            "memory": {"available_bytes": None, "total_bytes": None},
            "home_disk": {"free_bytes": 100, "total_bytes": 200},
            "reality": "OBSERVED_HOST",
            "resource_reservation": "NONE",
        }
        with patch.object(bridge, "AGENT_ID", "windows-bridge-test"), patch.object(
            bridge, "resource_snapshot", return_value=fake_snapshot
        ), patch.object(bridge, "request_json", side_effect=[
            {"ok": True, "status": "HEARTBEAT", "agent_id": "windows-bridge-test"},
            {"ok": True, "status": "TASK_AVAILABLE", "task": {
                "task_id": "test-task-003", "task": "python_version"
            }},
            {"ok": True, "status": "COMPLETED", "task": {
                "task_id": "different-task-id"
            }},
        ]):
            with self.assertRaisesRegex(RuntimeError, "REPORT_NOT_CONFIRMED"):
                bridge.run_once("unit-test-key")


if __name__ == "__main__":
    unittest.main()
