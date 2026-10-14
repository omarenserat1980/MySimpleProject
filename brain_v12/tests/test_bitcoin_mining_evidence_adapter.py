"""Offline tests for the Stratum-to-evidence adapter; no pool/network access."""
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from brain_v12.brain.bitcoin_mining_evidence_adapter import evaluate_mining_evidence


class BitcoinMiningEvidenceAdapterTests(unittest.TestCase):
    def setUp(self):
        self.probe = {
            "schema_version": "1.0",
            "mode": "connection_probe_only",
            "pool_host": "pool.example.invalid",
            "pool_port": 3333,
            "protocol": "stratum-v1",
            "subscribed": True,
            "authorized": True,
            "observed_at_utc": datetime.now(timezone.utc).isoformat(),
            "live_mining_verified": False,
            "accepted_shares_verified": False,
            "revenue_verified": False,
        }
        self.hashrate = {
            "value": 1200.0, "unit": "H/s", "window_seconds": 60,
            "source": "configured-worker-api",
        }
        self.shares = {
            "accepted_total": 1, "accepted_interval": 1,
            "rejected_total": 0, "stale_total": 0,
            "source": "configured-pool-api",
        }
        self.sources = {"configured-worker-api", "configured-pool-api"}

    def test_probe_alone_cannot_pass_gate(self):
        result = evaluate_mining_evidence(
            self.probe, worker_id="worker-1", hashrate=None, shares=None,
            trusted_source_ids=self.sources,
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["revenue_status"], "UNVERIFIED")
        self.assertFalse(result["execution_authorized"])

    def test_untrusted_hashrate_source_blocks(self):
        hashrate = dict(self.hashrate, source="unknown-source")
        result = evaluate_mining_evidence(
            self.probe, worker_id="worker-1", hashrate=hashrate,
            shares=self.shares, trusted_source_ids=self.sources,
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("HASHRATE_SOURCE_NOT_TRUSTED", result["failures"])

    def test_untrusted_share_source_blocks(self):
        shares = dict(self.shares, source="unknown-source")
        result = evaluate_mining_evidence(
            self.probe, worker_id="worker-1", hashrate=self.hashrate,
            shares=shares, trusted_source_ids=self.sources,
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("SHARE_SOURCE_NOT_TRUSTED", result["failures"])

    def test_missing_accepted_share_blocks(self):
        shares = dict(self.shares, accepted_total=0, accepted_interval=0)
        result = evaluate_mining_evidence(
            self.probe, worker_id="worker-1", hashrate=self.hashrate,
            shares=shares, trusted_source_ids=self.sources,
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("no_accepted_share", result["failures"])

    def test_fixture_is_rejected_and_revenue_stays_unverified(self):
        result = evaluate_mining_evidence(
            self.probe, worker_id="worker-1", hashrate=self.hashrate,
            shares=self.shares, trusted_source_ids=self.sources, fixture=True,
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["revenue_status"], "UNVERIFIED")
        self.assertFalse(result["execution_authorized"])

    @patch("brain_v12.brain.bitcoin_mining_evidence_adapter.validate_live_mining_evidence")
    def test_complete_record_is_sent_to_gate_but_revenue_is_not_inferred(self, validate):
        validate.return_value = {
            "status": "PASS", "gate": "MINING_ACTIVITY_VERIFIED",
            "failures": [], "revenue_status": "NOT_ASSESSED_BY_MINING_ACTIVITY_GATE",
        }
        result = evaluate_mining_evidence(
            self.probe, worker_id="worker-1", hashrate=self.hashrate,
            shares=self.shares, trusted_source_ids=self.sources,
        )
        validate.assert_called_once()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["revenue_status"], "UNVERIFIED")
        self.assertFalse(result["execution_authorized"])


if __name__ == "__main__":
    unittest.main()
