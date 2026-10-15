import unittest
from unittest.mock import patch

from brain_v12.brain.digital_mining_node import inspect_node


class DigitalMiningNodeTests(unittest.TestCase):
    def test_empty_environment_fails_closed_without_claiming_verification(self):
        with patch("brain_v12.brain.digital_mining_node._memory_bytes", return_value=1024), patch(
            "brain_v12.brain.digital_mining_node._temperature_sensor_available", return_value=True
        ), patch("brain_v12.brain.digital_mining_node.platform.system", return_value="Linux"), patch(
            "brain_v12.brain.digital_mining_node.Path.is_dir", return_value=False
        ), patch("brain_v12.brain.digital_mining_node.shutil.which", return_value=None):
            result = inspect_node({})
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["node_verified"])
        self.assertFalse(result["real_mining_started"])
        self.assertIn("NOT_RUNNING_IN_TERMUX", result["blockers"])
        self.assertIn("BRAIN_WORKER_AUTH_TOKEN_NOT_CONFIGURED", result["blockers"])

    def test_complete_local_preflight_still_does_not_claim_remote_verification(self):
        env = {
            "TERMUX_VERSION": "test",
            "BRAIN_CPUMINER_BIN": "/trusted/cpuminer",
            "BRAIN_MINING_POOL_URL": "configured",
            "BRAIN_MINING_WORKER": "configured",
            "V12_BRAIN_URL": "configured",
            "BRAIN_WORKER_TOKEN": "secret-not-output",
        }
        with patch("brain_v12.brain.digital_mining_node._memory_bytes", return_value=1024), patch(
            "brain_v12.brain.digital_mining_node._temperature_sensor_available", return_value=True
        ), patch("brain_v12.brain.digital_mining_node.platform.system", return_value="Linux"), patch(
            "brain_v12.brain.digital_mining_node.Path.is_file", return_value=True
        ), patch("brain_v12.brain.digital_mining_node.Path.is_dir", return_value=False):
            result = inspect_node(env)
        self.assertEqual(result["status"], "PREFLIGHT_READY_NOT_VERIFIED")
        self.assertFalse(result["node_verified"])
        self.assertFalse(result["accepted_shares_verified"])
        self.assertFalse(result["revenue_verified"])
        self.assertNotIn("secret-not-output", str(result))
        self.assertNotIn("configured", str(result))


if __name__ == "__main__":
    unittest.main()
