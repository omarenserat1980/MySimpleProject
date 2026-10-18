"""Regression tests for live-worker protocol consumption using in-memory lines only."""
from __future__ import annotations

import io
import json
import unittest

from brain_v12.brain.stratum_one_shot_tls_worker import (
    OneShotWorkerError,
    _consume_until,
)
from brain_v12.brain.stratum_v1_protocol import StratumV1Session


def wire(message: dict) -> bytes:
    return (json.dumps(message, separators=(",", ":")) + "\n").encode("utf-8")


def valid_notify(job_id: str = "job-regression") -> dict:
    return {
        "method": "mining.notify",
        "params": [
            job_id,
            "00" * 32,
            "01020304",
            "aabbccdd",
            ["11" * 32],
            "20000000",
            "ffff001d",
            "65aa0000",
            True,
        ],
    }


class OneShotWorkerProtocolRegressionTests(unittest.TestCase):
    def test_notifications_received_during_subscribe_are_preserved(self):
        session = StratumV1Session("account.worker01", "fixture-password")
        session.request_subscribe()
        stream = io.BytesIO(
            wire({"method": "mining.set_difficulty", "params": [1]})
            + wire({"method": "mining.set_extranonce", "params": ["abcd", 2]})
            + wire(valid_notify())
            + wire({"id": 1, "result": [[], "abcd", 2], "error": None})
        )

        outcome, job = _consume_until(
            session,
            stream,
            predicate=lambda result, message: result.get("purpose") == "subscribe",
            max_lines=10,
        )

        self.assertEqual(outcome["purpose"], "subscribe")
        self.assertTrue(session.subscribed)
        self.assertEqual(session.difficulty, 1.0)
        self.assertEqual(session.extranonce1_hex, "abcd")
        self.assertEqual(session.extranonce2_size, 2)
        self.assertEqual(session.current_job_id, "job-regression")
        self.assertIsNotNone(job)
        self.assertEqual(job.job_id, "job-regression")

    def test_malformed_line_fails_closed_without_echoing_payload(self):
        session = StratumV1Session("account.worker01", "fixture-password")
        with self.assertRaisesRegex(OneShotWorkerError, "STRATUM_PROTOCOL_ERROR"):
            _consume_until(
                session,
                io.BytesIO(b"{not-json}\n"),
                predicate=lambda result, message: False,
                max_lines=1,
            )

    def test_share_acceptance_requires_matching_pending_request(self):
        session = StratumV1Session("account.worker01", "fixture-password")
        session.request_subscribe()
        session.receive(wire({"id": 1, "result": [[], "abcd", 2], "error": None}))
        session.request_authorize()
        session.receive(wire({"id": 2, "result": True, "error": None}))
        session.current_job_id = "job-regression"
        session.active_job_ids.add("job-regression")
        submit = session.request_submit("job-regression", "0000", "65aa0000", "00000001")
        request = json.loads(submit)
        outcome = session.receive(wire({"id": request["id"], "result": True, "error": None}))
        self.assertEqual(outcome["event"], "SHARE_RESPONSE")
        self.assertEqual(outcome["status"], "ACCEPTED_BY_POOL")
        self.assertFalse(session.pending)

    def test_unmatched_share_response_is_rejected(self):
        session = StratumV1Session("account.worker01", "fixture-password")
        with self.assertRaisesRegex(Exception, "UNMATCHED_RESPONSE_ID"):
            session.receive(wire({"id": 99, "result": True, "error": None}))


if __name__ == "__main__":
    unittest.main()
