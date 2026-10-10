import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
AGENT_PATH = ROOT / "brain_windows_agent" / "arkan_heartbeat_agent.py"
SPEC = importlib.util.spec_from_file_location("arkan_heartbeat_agent", AGENT_PATH)
AGENT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AGENT)

class ArkanHeartbeatAgentTests(unittest.TestCase):
    def test_remote_url_requires_https(self):
        self.assertEqual(AGENT.validate_brain_url("https://brain.example.test/"), "https://brain.example.test")
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            AGENT.validate_brain_url("http://brain.example.test")

    def test_loopback_http_allowed_for_local_development(self):
        self.assertEqual(AGENT.validate_brain_url("http://127.0.0.1:8012/"), "http://127.0.0.1:8012")

    def test_credentials_in_url_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "INVALID"):
            AGENT.validate_brain_url("https://user:pass@brain.example.test")

    def test_metadata_never_claims_identity_or_execution_authority(self):
        metadata = AGENT.build_metadata()
        self.assertFalse(metadata["identity_verified"])
        self.assertFalse(metadata["execution_eligible"])
        self.assertFalse(metadata["task_execution_enabled"])
        self.assertEqual(metadata["capabilities"], ["heartbeat", "readonly_host_metadata"])

if __name__ == "__main__":
    unittest.main()
