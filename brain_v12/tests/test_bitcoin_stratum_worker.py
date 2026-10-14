"""Unit tests for the fail-closed Bitcoin Stratum V1 probe."""
import unittest

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
        self.assertEqual(
            __import__("json").loads(payload),
            {"id": 1, "method": "mining.subscribe", "params": ["test-client"]},
        )

    def test_only_supported_methods_are_allowed(self):
        with self.assertRaisesRegex(ValueError, "UNSUPPORTED_STRATUM_METHOD"):
            encode_request(1, "mining.submit", [])

    def test_response_requires_matching_id(self):
        with self.assertRaisesRegex(StratumProtocolError, "UNEXPECTED_RESPONSE_ID"):
            parse_response(b'{"id":7,"result":true,"error":null}', 1)

    def test_pool_rejection_does_not_leak_server_details(self):
        with self.assertRaisesRegex(StratumProtocolError, "STRATUM_REQUEST_REJECTED") as ctx:
            parse_response(b'{"id":1,"result":null,"error":[20,"secret-ish detail",null]}', 1)
        self.assertNotIn("secret-ish detail", str(ctx.exception))

    def test_live_probe_is_disabled_by_default(self):
        with self.assertRaisesRegex(RuntimeError, "LIVE_POOL_PROBE_DISABLED"):
            probe_stratum_v1(
                host="pool.example", port=3333, worker_name="worker",
                worker_password="password",
            )

    def test_invalid_port_is_rejected_before_network_access(self):
        with self.assertRaisesRegex(ValueError, "INVALID_POOL_PORT"):
            probe_stratum_v1(
                host="pool.example", port=70000, worker_name="worker",
                worker_password="password", enabled=True,
            )


if __name__ == "__main__":
    unittest.main()
