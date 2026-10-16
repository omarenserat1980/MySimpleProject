from datetime import datetime, timezone
import unittest

from brain_v12.brain.bitcoin_mining_evidence_gate import (
    canonical_digest,
    validate_live_mining_evidence,
)


def valid_record():
    record = {
        "schema_version": "1.0",
        "observed_at_utc": "2026-10-14T12:00:00Z",
        "mode": "live",
        "worker_id": "authorized-worker-1",
        "pool": {
            "host": "pool.example.invalid",
            "port": 3333,
            "protocol": "stratum",
            "connected": True,
            "authorized": True,
            "connected_at_utc": "2026-10-14T11:59:00Z",
            "source": "worker-api",
        },
        "hashrate": {
            "value": 1000.0,
            "unit": "H/s",
            "window_seconds": 60,
            "source": "worker-api",
        },
        "shares": {
            "accepted_total": 1,
            "accepted_interval": 1,
            "rejected_total": 0,
            "stale_total": 0,
            "source": "pool-api",
        },
        "fixture": False,
    }
    record["evidence_artifact_sha256"] = canonical_digest(record)
    return record


class BitcoinMiningEvidenceGateTests(unittest.TestCase):
    def test_valid_record_passes_activity_gate_only(self):
        record = valid_record()
        now = datetime(2026, 10, 14, 12, 1, tzinfo=timezone.utc)
        result = validate_live_mining_evidence(record, now=now)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["revenue_status"], "NOT_ASSESSED_BY_MINING_ACTIVITY_GATE")

    def test_fixture_never_passes(self):
        record = valid_record()
        record["fixture"] = True
        record["evidence_artifact_sha256"] = canonical_digest(record)
        result = validate_live_mining_evidence(
            record, now=datetime(2026, 10, 14, 12, 1, tzinfo=timezone.utc)
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("fixture_or_fixture_flag_missing", result["failures"])

    def test_no_accepted_share_blocks(self):
        record = valid_record()
        record["shares"]["accepted_total"] = 0
        record["shares"]["accepted_interval"] = 0
        record["evidence_artifact_sha256"] = canonical_digest(record)
        result = validate_live_mining_evidence(
            record, now=datetime(2026, 10, 14, 12, 1, tzinfo=timezone.utc)
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("no_accepted_share", result["failures"])

    def test_digest_tampering_blocks(self):
        record = valid_record()
        record["hashrate"]["value"] = 2000
        result = validate_live_mining_evidence(
            record, now=datetime(2026, 10, 14, 12, 1, tzinfo=timezone.utc)
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("evidence_digest_mismatch", result["failures"])

    def test_stale_evidence_blocks(self):
        record = valid_record()
        now = datetime(2026, 10, 14, 13, 0, tzinfo=timezone.utc)
        result = validate_live_mining_evidence(record, now=now)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("evidence_stale", result["failures"])


if __name__ == "__main__":
    unittest.main()
