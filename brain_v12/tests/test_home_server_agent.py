"""Tests for the standalone outbound Home Server worker."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

AGENT_PATH = Path(__file__).resolve().parents[2] / "v12-agent" / "home_server_agent.py"
SPEC = importlib.util.spec_from_file_location("brain_home_server_agent", AGENT_PATH)
agent = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(agent)


class HomeServerAgentTests(unittest.TestCase):
    def test_allowlisted_python_version(self):
        result = agent.execute_task("python_version")
        self.assertTrue(result["python"])
        self.assertTrue(result["executable"])

    def test_arbitrary_command_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "TASK_NOT_ALLOWED"):
            agent.execute_task("shell", {"command": "whoami"})

    def test_claim_execute_and_report_round_trip(self):
        responses = [
            {"ok": True, "status": "TASK_AVAILABLE", "task": {
                "task_id": "home-test-1", "task": "python_version", "params": {}
            }},
            {"ok": True, "task": {"task_id": "home-test-1", "status": "COMPLETED"}},
        ]
        calls = []

        def fake_request(method, path, key, payload=None):
            calls.append((method, path, payload))
            return responses.pop(0)

        with patch.object(agent, "request_json", side_effect=fake_request):
            result = agent.run_once("test-key")

        self.assertTrue(result["ok"])
        self.assertEqual(result["task_id"], "home-test-1")
        self.assertEqual(result["reported_status"], "COMPLETED")
        self.assertEqual(calls[0][1], "/api/home-server/claim")
        self.assertEqual(calls[1][1], "/api/home-server/tasks/home-test-1/report")
        self.assertEqual(calls[1][2]["worker_id"], agent.AGENT_ID)
        self.assertTrue(calls[1][2]["ok"])
        self.assertIn("python", calls[1][2]["result"])


if __name__ == "__main__":
    unittest.main()
