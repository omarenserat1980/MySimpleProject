import importlib.util
import os
import pathlib
import unittest
from unittest.mock import patch

MODULE_PATH = pathlib.Path(__file__).resolve().parents[2] / "brain_emulator_agent" / "v12_agent.py"


class BrainTermuxEmulatorRuntimeTests(unittest.TestCase):
    def test_agent_boots_heartbeats_polls_executes_and_reports_allowlisted_task(self):
        env = {
            "BRAIN_URL": "http://127.0.0.1:9",
            "BRAIN_EMULATOR_KEY": "test-only-not-a-real-secret",
            "BRAIN_EMULATOR_ID": "brain-termux-virtual-test",
            "BRAIN_EMULATOR_MAX_TASKS_PER_RUN": "1",
            "BRAIN_EMULATOR_POLL_SECONDS": "1",
            "BRAIN_EMULATOR_HEARTBEAT_SECONDS": "5",
            "BRAIN_AGENT_AUTO_SELF_TEST": "0",
        }
        with patch.dict(os.environ, env, clear=False):
            spec = importlib.util.spec_from_file_location("brain_termux_agent_under_test", MODULE_PATH)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

        calls = []
        def fake_request(method, path, payload=None, params=None):
            calls.append((method, path, payload, params))
            if method == "GET" and path == "/api/device/poll":
                return {"task": {"task_id": "runtime-proof-001", "task": "status", "params": {}}}
            if method == "POST" and path == "/api/device/report":
                return {"ok": True, "status": "REPORTED"}
            return {"ok": True}

        with patch.object(module, "request", side_effect=fake_request):
            module.main()

        paths = [(method, path) for method, path, _, _ in calls]
        self.assertIn(("POST", "/api/device/heartbeat"), paths)
        self.assertIn(("GET", "/api/device/poll"), paths)
        reports = [payload for method, path, payload, _ in calls if method == "POST" and path == "/api/device/report"]
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]["task_id"], "runtime-proof-001")
        self.assertEqual(reports[0]["agent_id"], "brain-termux-virtual-test")
        self.assertTrue(reports[0]["ok"])
        self.assertEqual(reports[0]["result"]["status"], "READY")


if __name__ == "__main__":
    unittest.main()
