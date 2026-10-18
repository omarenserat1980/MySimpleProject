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

    def test_rejects_non_numeric_timeout_cleanly(self):
        env = {
            "BRAIN_ENABLE_LIVE_STRATUM_BRIDGE": "1",
            "BRAIN_STRATUM_HOST": "pool.example.invalid",
            "BRAIN_STRATUM_PORT": "3333",
            "BRAIN_STRATUM_USERNAME": "account.worker",
            "BRAIN_STRATUM_PASSWORD": "secret",
            "BRAIN_STRATUM_TLS": "1",
            "BRAIN_MINING_WORKER_OWNED": "1",
            "BRAIN_MINING_AUTHORIZED": "1",
        }
        with patch.dict(os.environ, env, clear=True):
            for timeout in ("not-a-number", None):
                with self.subTest(timeout=timeout):
                    with self.assertRaisesRegex(StratumBridgeError, "TIMEOUT_OUT_OF_RANGE"):
                        probe_stratum_connection(timeout_seconds=timeout)

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


    def test_successful_tls_probe_reports_connectivity_only(self):
        import io
        import json
        from unittest.mock import MagicMock

        env = {
            "BRAIN_ENABLE_LIVE_STRATUM_BRIDGE": "1",
            "BRAIN_STRATUM_HOST": "pool.example.test",
            "BRAIN_STRATUM_PORT": "443",
            "BRAIN_STRATUM_USERNAME": "account.worker",
            "BRAIN_STRATUM_PASSWORD": "test-password-not-real",
            "BRAIN_STRATUM_TLS": "1",
            "BRAIN_MINING_WORKER_OWNED": "1",
            "BRAIN_MINING_AUTHORIZED": "1",
        }
        raw_socket = MagicMock()
        tls_socket = MagicMock()
        tls_socket.makefile.side_effect = [
            io.StringIO(json.dumps({"id": 1, "result": [[], "aabb", 4], "error": None}) + "\\n"
                        + json.dumps({"id": 2, "result": True, "error": None}) + "\\n"),
            io.StringIO(),
        ]
        # Keep the writer's bytes inspectable after the probe returns.
        writer = io.StringIO()
        tls_socket.makefile.side_effect = [
            io.StringIO(json.dumps({"id": 1, "result": [[], "aabb", 4], "error": None}) + "\\n"
                        + json.dumps({"id": 2, "result": True, "error": None}) + "\\n"),
            writer,
        ]
        tls_context = MagicMock()
        tls_context.wrap_socket.return_value = tls_socket
        with patch.dict(os.environ, env, clear=True), \\
             patch("brain_v12.brain.bitcoin_stratum_bridge.socket.create_connection", return_value=raw_socket), \\
             patch("brain_v12.brain.bitcoin_stratum_bridge.ssl.create_default_context", return_value=tls_context):
            result = probe_stratum_connection()

        self.assertEqual(result["status"], "STRATUM_SESSION_AUTHENTICATED")
        self.assertTrue(result["tls"])
        self.assertFalse(result["proof_of_work_performed"])
        self.assertEqual(result["shares_submitted"], 0)
        self.assertEqual(result["accepted_shares"], 0)
        self.assertFalse(result["execution_authorized"])
        self.assertNotIn("test-password-not-real", repr(result))
        requests = [json.loads(line) for line in writer.getvalue().splitlines()]
        self.assertEqual([request["method"] for request in requests], ["mining.subscribe", "mining.authorize"])
        self.assertEqual(requests[1]["params"], ["account.worker", "test-password-not-real"])
        tls_context.wrap_socket.assert_called_once_with(raw_socket, server_hostname="pool.example.test")

    def test_tls_probe_fails_closed_when_subscribe_is_rejected(self):
        import io
        import json
        from unittest.mock import MagicMock

        env = {
            "BRAIN_ENABLE_LIVE_STRATUM_BRIDGE": "1",
            "BRAIN_STRATUM_HOST": "pool.example.test",
            "BRAIN_STRATUM_PORT": "443",
            "BRAIN_STRATUM_USERNAME": "account.worker",
            "BRAIN_STRATUM_PASSWORD": "test-password-not-real",
            "BRAIN_STRATUM_TLS": "1",
            "BRAIN_MINING_WORKER_OWNED": "1",
            "BRAIN_MINING_AUTHORIZED": "1",
        }
        raw_socket = MagicMock()
        tls_socket = MagicMock()
        tls_socket.makefile.side_effect = [
            io.StringIO(json.dumps({"id": 1, "result": None, "error": [20, "rejected", None]}) + "\\n"),
            io.StringIO(),
        ]
        tls_context = MagicMock()
        tls_context.wrap_socket.return_value = tls_socket
        with patch.dict(os.environ, env, clear=True), \\
             patch("brain_v12.brain.bitcoin_stratum_bridge.socket.create_connection", return_value=raw_socket), \\
             patch("brain_v12.brain.bitcoin_stratum_bridge.ssl.create_default_context", return_value=tls_context):
            with self.assertRaisesRegex(StratumBridgeError, "SUBSCRIBE_REJECTED"):
                probe_stratum_connection()


if __name__ == "__main__":
    unittest.main()
