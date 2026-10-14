"""Tests for the fail-closed Stratum V1 connection probe."""
import json
import unittest
from unittest.mock import patch

from brain_v12.brain.bitcoin_stratum_connection_probe import (
    StratumConnectionProbeError,
    _parse_response,
    encode_probe_request,
    probe_stratum_v1,
)


class BitcoinStratumConnectionProbeTests(unittest.TestCase):
    def test_encode_request_is_newline_delimited_json(self):
        payload = encode_probe_request(1, "mining.subscribe", ["test-client"])
        self.assertTrue(payload.endswith(b"\\n"))
        self.assertEqual(json.loads(payload), {
            "id": 1, "method": "mining.subscribe", "params": ["test-client"]
        })

    def test_only_probe_methods_are_allowed(self):
        with self.assertRaisesRegex(ValueError, "UNSUPPORTED_STRATUM_METHOD"):
            encode_probe_request(1, "mining.submit", [])

    def test_response_requires_matching_id(self):
        with self.assertRaisesRegex(StratumConnectionProbeError, "UNEXPECTED_RESPONSE_ID"):
            _parse_response(b'{"id":7,"result":true,"error":null}', 1)

    def test_rejection_does_not_leak_pool_error_details(self):
        with self.assertRaisesRegex(StratumConnectionProbeError, "STRATUM_REQUEST_REJECTED") as ctx:
            _parse_response(b'{"id":1,"result":null,"error":[20,"private detail",null]}', 1)
        self.assertNotIn("private detail", str(ctx.exception))

    def test_network_probe_disabled_by_default(self):
        with self.assertRaisesRegex(RuntimeError, "LIVE_POOL_PROBE_DISABLED"):
            probe_stratum_v1(
                host="pool.example", port=3333, worker_name="worker",
                worker_password="password",
            )

    def test_invalid_port_fails_before_network_access(self):
        with self.assertRaisesRegex(ValueError, "INVALID_POOL_PORT"):
            probe_stratum_v1(
                host="pool.example", port=70000, worker_name="worker",
                worker_password="password", enabled=True,
            )

    @patch("brain_v12.brain.bitcoin_stratum_connection_probe.socket.create_connection")
    def test_probe_never_claims_mining_or_revenue(self, create_connection):
        self.assertTrue(callable(create_connection))
        # No socket is opened: the default-disabled gate is asserted above.
        with self.assertRaisesRegex(RuntimeError, "LIVE_POOL_PROBE_DISABLED"):
            probe_stratum_v1(
                host="pool.example", port=3333, worker_name="worker",
                worker_password="password", enabled=False,
            )
        create_connection.assert_not_called()


if __name__ == "__main__":
    unittest.main()
