import importlib.util
import os
import unittest
from pathlib import Path

AGENT_PATH = Path(__file__).resolve().parents[2] / "v12-agent" / "agent.py"

class TermuxAgentContractTests(unittest.TestCase):
    def setUp(self):
        self.env_keys = ("V12_BRAIN_URL", "V12_AGENT_ID")
        self.old_env = {key: os.environ.get(key) for key in self.env_keys}
        for key in self.env_keys:
            os.environ.pop(key, None)
        spec = importlib.util.spec_from_file_location("v12_termux_agent_contract", AGENT_PATH)
        self.agent = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.agent)

    def tearDown(self):
        for key, value in self.old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_defaults_target_current_service_and_software_identity(self):
        self.assertEqual(self.agent.BRAIN_URL, "https://mysimpleproject.onrender.com")
        self.assertEqual(self.agent.AGENT_ID, "software-executor-redmi3-01")

    def test_heartbeat_metadata_identifies_software_not_hardware(self):
        metadata = self.agent.heartbeat_metadata()
        self.assertEqual(metadata["node_type"], "software")
        self.assertEqual(metadata["runtime"], "termux")
        self.assertNotIn("cpu_cores", metadata)
        self.assertNotIn("memory_mb", metadata)
        self.assertNotIn("disk_mb", metadata)

    def test_agent_rejects_unlisted_shell_execution(self):
        with self.assertRaises(ValueError):
            self.agent.execute("shell", {})

if __name__ == "__main__":
    unittest.main()
