import unittest
from datetime import datetime, timezone
from brain_v12.brain.bitcoin_stratum_evidence import canonical_sha256, validate_stratum_evidence


class BitcoinStratumEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)
        self.payload = {
            "schema_version": 1, "worker_id": "owned-worker-01",
            "algorithm": "sha256d", "pool_host": "pool.example.invalid",
            "observed_at": "2026-10-15T11:59:00Z", "window_seconds": 60,
            "hashrate_hs": 1000.0, "accepted_shares": 2,
            "rejected_shares": 0, "stale_shares": 0,
            "connection_state": "CONNECTED",
        }
        self.payload["evidence_sha256"] = canonical_sha256(self.payload)

    def test_valid_schema_never_authorizes_mining_or_revenue(self):
        result = validate_stratum_evidence(self.payload, now=self.now)
        self.assertTrue(result["valid"], result["errors"])
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["revenue_verified"])

    def test_tampering_fails_digest(self):
        self.payload["accepted_shares"] = 999
        result = validate_stratum_evidence(self.payload, now=self.now)
        self.assertFalse(result["valid"])
        self.assertIn("EVIDENCE_DIGEST_MISMATCH", result["errors"])

    def test_stale_evidence_is_blocked(self):
        self.payload["observed_at"] = "2026-10-15T10:00:00Z"
        self.payload["evidence_sha256"] = canonical_sha256(self.payload)
        result = validate_stratum_evidence(self.payload, now=self.now)
        self.assertIn("STALE_EVIDENCE", result["errors"])

    def test_wrong_algorithm_is_blocked(self):
        self.payload["algorithm"] = "randomx"
        self.payload["evidence_sha256"] = canonical_sha256(self.payload)
        result = validate_stratum_evidence(self.payload, now=self.now)
        self.assertIn("ALGORITHM_NOT_BITCOIN_SHA256D", result["errors"])


if __name__ == "__main__":
    unittest.main()
