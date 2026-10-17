import unittest

from brain_v12.brain.stratum_protocol_contract import (
    StratumProtocolError,
    build_authorize_request,
    build_submit_request,
    build_subscribe_request,
    parse_difficulty,
    parse_json_line,
    parse_notify,
    parse_response,
)


class StratumProtocolContractTests(unittest.TestCase):
    def test_subscribe_request_shape(self):
        self.assertEqual(
            build_subscribe_request(1, "ElectronicBrain/0.1"),
            {"id": 1, "method": "mining.subscribe", "params": ["ElectronicBrain/0.1"]},
        )

    def test_authorize_payload_is_only_constructed(self):
        payload = build_authorize_request(2, "worker.1", "secret")
        self.assertEqual(payload["method"], "mining.authorize")
        self.assertEqual(payload["params"], ["worker.1", "secret"])

    def test_submit_request_validates_hex_fields(self):
        payload = build_submit_request(3, "worker.1", "job-1", "aabb", "01234567", "89abcdef")
        self.assertEqual(payload["method"], "mining.submit")
        self.assertEqual(payload["params"], ["worker.1", "job-1", "aabb", "01234567", "89abcdef"])

    def test_rejects_invalid_hex_nonce(self):
        with self.assertRaises(StratumProtocolError):
            build_submit_request(3, "worker.1", "job-1", "aabb", "01234567", "xyzxyz12")

    def test_rejects_multiple_frames_and_non_object_json(self):
        with self.assertRaises(StratumProtocolError):
            parse_json_line('{"id":1}\n{"id":2}')
        with self.assertRaises(StratumProtocolError):
            parse_json_line('["not", "an object"]')

    def test_parses_response_without_claiming_independent_proof(self):
        result = parse_response({"id": 7, "result": True, "error": None}, 7)
        self.assertTrue(result["accepted"])
        self.assertIn("requires_transport", result["source"])
        with self.assertRaises(StratumProtocolError):
            parse_response({"id": 8, "result": True, "error": None}, 7)

    def test_difficulty_must_be_positive_and_finite(self):
        self.assertEqual(parse_difficulty([2.5]), 2.5)
        for invalid in ([0], [-1], [float("inf")], [True], []):
            with self.subTest(invalid=invalid), self.assertRaises(StratumProtocolError):
                parse_difficulty(invalid)

    def test_notify_is_untrusted_job_data(self):
        job = parse_notify([
            "job-1", "00" * 32, "aa", "bb", ["cc" * 32],
            "20000000", "1d00ffff", "65000000", True,
        ])
        self.assertEqual(job["job_id"], "job-1")
        self.assertFalse(job["share_accepted"])
        with self.assertRaises(StratumProtocolError):
            parse_notify(["too", "short"])


if __name__ == "__main__":
    unittest.main()
