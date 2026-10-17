"""Regression tests for the Termux software worker contract."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

AGENT_PATH = Path(__file__).resolve().parents[2] / "v12-agent" / "agent.py"
SPEC = importlib.util.spec_from_file_location("v12_termux_agent", AGENT_PATH)
agent = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(agent)


class TermuxAgentContractTests(unittest.TestCase):
    def test_default_identity_matches_android_executor_registry(self):
        self.assertTrue(agent.AGENT_ID.startswith("android-executor-"))
        self.assertEqual(agent.BRAIN_URL, "https://brain-control-plane-main.onrender.com")

    def test_heartbeat_metadata_marks_software_node(self):
        metadata = agent.heartbeat_metadata()
        self.assertEqual(metadata["node_type"], "software")
        self.assertEqual(metadata["runtime"], "termux")

    def test_unlisted_tasks_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "task_not_allowed"):
            agent.execute("shell", {"command": "id"})

    def test_authenticated_request_carries_agent_identity_and_key(self):
        class FakeResponse:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self):
                return b'{"ok": true}'

        with patch.object(agent.urllib.request, "urlopen", return_value=FakeResponse()) as urlopen:
            result = agent.request("GET", "/api/device/status", key="test-only-not-a-real-secret")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("X-v12-agent-id"), agent.AGENT_ID)
        self.assertEqual(request.get_header("X-v12-agent-key"), "test-only-not-a-real-secret")
        self.assertEqual(result, {"ok": True})


if __name__ == "__main__":
    unittest.main()
