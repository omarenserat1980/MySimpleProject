"""Offline tests for the Stratum V1 share-submission payload contract."""
import json
import unittest

from brain_v12.brain.stratum_share_submission_contract import (
    build_session_share_submission,
    build_share_submission,
    encode_share_submission,
)
from brain_v12.brain.stratum_v1_protocol import StratumV1Session


class StratumShareSubmissionContractTests(unittest.TestCase):
    def valid(self):
        return {
            "request_id": 3,
            "worker_name": "account.worker01",
            "job_id": "job-42",
            "extranonce2": "a1b2",
            "ntime": "65aa0000",
            "nonce": "0000002a",
        }

    def authorized_session(self):
        session = StratumV1Session("account.worker01", "test-password")
        session.request_subscribe()
        session.receive(json.dumps({
            "id": 1, "result": [[], "abcd", 2], "error": None
        }))
        session.request_authorize()
        session.receive(json.dumps({"id": 2, "result": True, "error": None}))
        session.receive(json.dumps({
            "method": "mining.notify",
            "params": [
                "job-42", "00" * 32, "", "", [], "20000000",
                "ffff001d", "65aa0000", True
            ]
        }))
        return session

    def test_builds_valid_request_without_sending(self):
        result = build_share_submission(**self.valid())
        self.assertEqual(result["method"], "mining.submit")
        self.assertEqual(result["params"], [
            "account.worker01", "job-42", "a1b2", "65aa0000", "0000002a"
        ])
        self.assertFalse(result["sent"])
        self.assertFalse(result["pool_acceptance_verified"])
        self.assertFalse(result["real_mining_verified"])
        self.assertFalse(result["revenue_verified"])

    def test_wire_encoding_is_newline_delimited_json_and_excludes_claim_fields(self):
        payload = encode_share_submission(**self.valid())
        self.assertTrue(payload.endswith(b"\n"))
        decoded = json.loads(payload)
        self.assertEqual(decoded["method"], "mining.submit")
        self.assertEqual(set(decoded), {"id", "method", "params"})
        self.assertNotIn(b"password", payload)

    def test_invalid_request_id_and_injection_are_rejected(self):
        for value in (True, 0, -1, "3"):
            args = self.valid()
            args["request_id"] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "INVALID_REQUEST_ID"):
                build_share_submission(**args)
        args = self.valid()
        args["worker_name"] = "worker\r\nmining.authorize"
        with self.assertRaisesRegex(ValueError, "INVALID_WORKER_NAME"):
            build_share_submission(**args)

    def test_malformed_job_and_hex_fields_are_rejected(self):
        for key, value, code in (
            ("job_id", "", "INVALID_JOB_ID"),
            ("extranonce2", "xyz1", "INVALID_EXTRANONCE2"),
            ("extranonce2", "abc", "INVALID_EXTRANONCE2"),
            ("ntime", "1234", "INVALID_NTIME"),
            ("ntime", "gggggggg", "INVALID_NTIME"),
            ("nonce", "0000000z", "INVALID_NONCE"),
        ):
            args = self.valid()
            args[key] = value
            with self.subTest(key=key, value=value), self.assertRaisesRegex(ValueError, code):
                build_share_submission(**args)

    def test_session_bound_builder_uses_existing_authorization_and_job_gates(self):
        session = self.authorized_session()
        result = build_session_share_submission(
            session, job_id="job-42", extranonce2="a1b2",
            ntime="65aa0000", nonce="0000002a",
        )
        self.assertEqual(result["method"], "mining.submit")
        self.assertEqual(result["params"], [
            "account.worker01", "job-42", "a1b2", "65aa0000", "0000002a"
        ])
        self.assertFalse(result["sent"])
        self.assertFalse(result["pool_acceptance_verified"])
        self.assertFalse(result["revenue_verified"])
        self.assertEqual(session.snapshot()["pending_requests"], 1)

    def test_session_bound_builder_rejects_unauthorized_and_stale_jobs(self):
        session = StratumV1Session("account.worker01", "test-password")
        with self.assertRaisesRegex(ValueError, "POOL_AUTHORIZATION_REQUIRED"):
            build_session_share_submission(
                session, job_id="job-42", extranonce2="a1b2",
                ntime="65aa0000", nonce="0000002a",
            )
        session = self.authorized_session()
        with self.assertRaisesRegex(ValueError, "UNKNOWN_OR_STALE_JOB"):
            build_session_share_submission(
                session, job_id="stale-job", extranonce2="a1b2",
                ntime="65aa0000", nonce="0000002a",
            )

    def test_session_bound_builder_rejects_wrong_negotiated_extranonce_width(self):
        session = self.authorized_session()
        with self.assertRaisesRegex(ValueError, "INVALID_EXTRANONCE2_NEGOTIATED_WIDTH"):
            build_session_share_submission(
                session, job_id="job-42", extranonce2="a1b2c3",
                ntime="65aa0000", nonce="0000002a",
            )


if __name__ == "__main__":
    unittest.main()
