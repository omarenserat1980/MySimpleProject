"""Offline tests for evidence classification of Stratum share responses."""
import json
import unittest

from brain_v12.brain.stratum_share_response_evidence import observe_share_response
from brain_v12.brain.stratum_v1_protocol import StratumProtocolError, StratumV1Session


class StratumShareResponseEvidenceTests(unittest.TestCase):
    def authorized_session_with_pending_share(self):
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
        session.request_submit("job-42", "a1b2", "65aa0000", "0000002a")
        return session

    def test_correlated_positive_response_is_only_pool_reported_acceptance(self):
        session = self.authorized_session_with_pending_share()
        evidence = observe_share_response(
            session, json.dumps({"id": 3, "result": True, "error": None})
        )
        self.assertEqual(evidence["pool_reported_status"], "ACCEPTED_BY_POOL")
        self.assertTrue(evidence["pool_reported_acceptance"])
        self.assertFalse(evidence["live_transport_verified"])
        self.assertFalse(evidence["independent_share_validation_verified"])
        self.assertFalse(evidence["payout_verified"])
        self.assertFalse(evidence["revenue_verified"])
        self.assertFalse(evidence["financial_execution_enabled"])
        self.assertEqual(session.accepted_shares, 1)
        self.assertNotIn(3, session.pending)

    def test_correlated_negative_response_is_classified_as_rejected(self):
        session = self.authorized_session_with_pending_share()
        evidence = observe_share_response(
            session, json.dumps({
                "id": 3, "result": False, "error": [20, "low difficulty", None]
            })
        )
        self.assertEqual(evidence["pool_reported_status"], "REJECTED_BY_POOL")
        self.assertFalse(evidence["pool_reported_acceptance"])
        self.assertFalse(evidence["revenue_verified"])
        self.assertEqual(session.rejected_shares, 1)

    def test_unmatched_response_fails_closed_without_mutating_pending_request(self):
        session = self.authorized_session_with_pending_share()
        with self.assertRaisesRegex(StratumProtocolError, "UNMATCHED_SHARE_RESPONSE"):
            observe_share_response(
                session, json.dumps({"id": 99, "result": True, "error": None})
            )
        self.assertIn(3, session.pending)
        self.assertEqual(session.accepted_shares, 0)
        self.assertEqual(session.rejected_shares, 0)

    def test_non_share_pending_request_cannot_be_classified_as_share(self):
        session = StratumV1Session("account.worker01", "test-password")
        session.request_subscribe()
        with self.assertRaisesRegex(StratumProtocolError, "UNMATCHED_SHARE_RESPONSE"):
            observe_share_response(
                session, json.dumps({"id": 1, "result": True, "error": None})
            )
        self.assertEqual(session.pending.get(1), "subscribe")


if __name__ == "__main__":
    unittest.main()
