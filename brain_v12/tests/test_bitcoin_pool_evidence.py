import unittest
from datetime import datetime, timezone, timedelta

from brain_v12.brain.bitcoin_pool_evidence import evidence_digest, validate_pool_evidence


class BitcoinPoolEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 14, 12, 0, 0, tzinfo=timezone.utc)
        self.record = {
            "schema_version": "1.0",
            "observed_at_utc": "2026-10-14T11:59:00Z",
            "mode": "live",
            "worker_id": "user-owned-worker-01",
            "pool": {
                "host": "pool.example.invalid",
                "port": 3333,
                "protocol": "stratum",
                "connected": True,
                "authorized": True,
                "connected_at_utc": "2026-10-14T11:58:00Z",
                "source": "pool-api",
            },
            "hashrate": {
                "value": 125000000000.0,
                "unit": "H/s",
                "window_seconds": 60,
                "source": "pool-api",
            },
            "shares": {
                "accepted_total": 9,
                "accepted_interval": 1,
                "rejected_total": 0,
                "stale_total": 0,
                "source": "pool-api",
            },
            "fixture": False,
        }
        self.record["evidence_artifact_sha256"] = evidence_digest(self.record)

    def test_valid_record_only_validates_activity_evidence_not_revenue(self):
        result = validate_pool_evidence(self.record, now=self.now)
        self.assertEqual(result["status"], "MINING_ACTIVITY_EVIDENCE_VALIDATED")
        self.assertTrue(result["mining_activity_verified"])
        self.assertFalse(result["payout_verified"])
        self.assertFalse(result["revenue_verified"])

    def test_fixture_is_rejected(self):
        self.record["fixture"] = True
        self.record["evidence_artifact_sha256"] = evidence_digest(self.record)
        result = validate_pool_evidence(self.record, now=self.now)
        self.assertIn("FIXTURE_OR_UNMARKED_EVIDENCE_FORBIDDEN", result["errors"])
        self.assertFalse(result["mining_activity_verified"])

    def test_stale_record_is_rejected(self):
        self.record["observed_at_utc"] = "2026-10-14T11:00:00Z"
        self.record["evidence_artifact_sha256"] = evidence_digest(self.record)
        result = validate_pool_evidence(self.record, now=self.now, max_age_seconds=300)
        self.assertIn("STALE_EVIDENCE", result["errors"])

    def test_missing_pool_accepted_share_is_rejected(self):
        self.record["shares"]["accepted_interval"] = 0
        self.record["evidence_artifact_sha256"] = evidence_digest(self.record)
        result = validate_pool_evidence(self.record, now=self.now)
        self.assertIn("AT_LEAST_ONE_ACCEPTED_SHARE_REQUIRED", result["errors"])

    def test_digest_mismatch_is_rejected(self):
        self.record["hashrate"]["value"] = 999
        result = validate_pool_evidence(self.record, now=self.now)
        self.assertIn("EVIDENCE_DIGEST_MISMATCH", result["errors"])

    def test_worker_log_alone_is_not_pool_side_share_proof(self):
        self.record["shares"]["source"] = "worker"
        self.record["evidence_artifact_sha256"] = evidence_digest(self.record)
        result = validate_pool_evidence(self.record, now=self.now)
        self.assertIn("POOL_SIDE_SHARE_EVIDENCE_REQUIRED", result["errors"])


if __name__ == "__main__":
    unittest.main()
