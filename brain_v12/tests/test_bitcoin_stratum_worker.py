"""Unit tests for the fail-closed Bitcoin Stratum V1 connection probe."""
import json
import unittest
from unittest.mock import patch

from brain_v12.brain.bitcoin_stratum_worker import (
    StratumProtocolError,
    encode_request,
    parse_response,
    probe_stratum_v1,
)


class BitcoinStratumWorkerTests(unittest.TestCase):
    def test_encode_request_is_newline_delimited_json(self):
        payload = encode_request(1, "mining.subscribe", ["test-client"])
        self.assertTrue(payload.endswith(b"\n"))
        self.assertEqual(json.loads(payload), {
            "id": 1, "method": "mining.subscribe", "params": ["test-client"]
        })

    def test_request_ids_and_methods_are_validated(self):
        with self.assertRaisesRegex(ValueError, "INVALID_REQUEST_ID"):
            encode_request(True, "mining.subscribe", [])
        with self.assertRaisesRegex(ValueError, "UNSUPPORTED_STRATUM_METHOD"):
            encode_request(1, "mining.submit", [])

    def test_response_requires_matching_integer_id(self):
        for payload in (
            b'{"id":7,"result":true,"error":null}',
            b'{"id":true,"result":true,"error":null}',
        ):
            with self.subTest(payload=payload), self.assertRaisesRegex(
                StratumProtocolError, "UNEXPECTED_RESPONSE_ID"
            ):
                parse_response(payload, 1)

    def test_pool_rejection_does_not_leak_server_details(self):
        with self.assertRaisesRegex(StratumProtocolError, "STRATUM_REQUEST_REJECTED") as ctx:
            parse_response(b'{"id":1,"result":null,"error":[20,"sensitive detail",null]}', 1)
        self.assertNotIn("sensitive detail", str(ctx.exception))

    def test_live_probe_is_disabled_by_default_without_network(self):
        with patch("brain_v12.brain.bitcoin_stratum_worker.socket.create_connection") as connect:
            with self.assertRaisesRegex(RuntimeError, "LIVE_POOL_PROBE_DISABLED"):
                probe_stratum_v1(
                    host="pool.example", port=3333, worker_name="worker",
                    worker_password="password",
                )
            connect.assert_not_called()

    def test_plaintext_probe_is_rejected_before_network_access(self):
        with patch("brain_v12.brain.bitcoin_stratum_worker.socket.create_connection") as connect:
            with self.assertRaisesRegex(ValueError, "STRATUM_TLS_REQUIRED"):
                probe_stratum_v1(
                    host="pool.example", port=3333, worker_name="worker",
                    worker_password="password", enabled=True, use_tls=False,
                )
            connect.assert_not_called()

    def test_invalid_port_is_rejected_before_network_access(self):
        with patch("brain_v12.brain.bitcoin_stratum_worker.socket.create_connection") as connect:
            with self.assertRaisesRegex(ValueError, "INVALID_POOL_PORT"):
                probe_stratum_v1(
                    host="pool.example", port=70000, worker_name="worker",
                    worker_password="password", enabled=True,
                )
            connect.assert_not_called()

    def test_empty_password_and_bad_timeout_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "INVALID_WORKER_PASSWORD"):
            probe_stratum_v1(
                host="pool.example", port=3333, worker_name="worker",
                worker_password="", enabled=True,
            )
        with self.assertRaisesRegex(ValueError, "TIMEOUT_OUT_OF_RANGE"):
            probe_stratum_v1(
                host="pool.example", port=3333, worker_name="worker",
                worker_password="x", timeout_seconds=float("nan"), enabled=True,
            )


if __name__ == "__main__":
    unittest.main()
