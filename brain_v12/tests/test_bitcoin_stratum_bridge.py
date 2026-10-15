import os
import unittest
from unittest.mock import patch

from brain_v12.brain.bitcoin_stratum_bridge import (
    StratumBridgeError, bridge_config_from_env, probe_stratum_connection,
)


class BitcoinStratumBridgeTests(unittest.TestCase):
    def test_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(bridge_config_from_env()["enabled"])
            with self.assertRaisesRegex(StratumBridgeError, "BRIDGE_DISABLED"):
                probe_stratum_connection()

    def test_refuses_ci_even_when_enabled(self):
        env = {
            "BRAIN_ENABLE_LIVE_STRATUM_BRIDGE": "1",
            "BRAIN_STRATUM_HOST": "pool.example.invalid",
            "BRAIN_STRATUM_PORT": "3333",
            "BRAIN_STRATUM_USERNAME": "account.worker",
            "BRAIN_STRATUM_PASSWORD": "secret",
            "BRAIN_MINING_WORKER_OWNED": "1",
            "BRAIN_MINING_AUTHORIZED": "1",
            "CI": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(StratumBridgeError, "FORBIDDEN_IN_CI"):
                probe_stratum_connection()

    def test_refuses_plaintext_stratum_before_sending_credentials(self):
        env = {
            "BRAIN_ENABLE_LIVE_STRATUM_BRIDGE": "1",
            "BRAIN_STRATUM_HOST": "pool.example.invalid",
            "BRAIN_STRATUM_PORT": "3333",
            "BRAIN_STRATUM_USERNAME": "account.worker",
            "BRAIN_STRATUM_PASSWORD": "secret",
            "BRAIN_MINING_WORKER_OWNED": "1",
            "BRAIN_MINING_AUTHORIZED": "1",
            "BRAIN_STRATUM_TLS": "0",
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(StratumBridgeError, "TLS_REQUIRED"):
                probe_stratum_connection()

    def test_requires_explicit_ownership(self):
        env = {
            "BRAIN_ENABLE_LIVE_STRATUM_BRIDGE": "1",
            "BRAIN_STRATUM_HOST": "pool.example.invalid",
            "BRAIN_STRATUM_PORT": "3333",
            "BRAIN_STRATUM_USERNAME": "account.worker",
            "BRAIN_STRATUM_PASSWORD": "secret",
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(StratumBridgeError, "OWNERSHIP_AND_AUTHORIZATION"):
                probe_stratum_connection()


if __name__ == "__main__":
    unittest.main()
