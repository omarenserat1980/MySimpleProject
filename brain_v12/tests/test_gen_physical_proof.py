"""Offline acceptance tests for the GEN physical-proof gate."""
import unittest
from datetime import datetime, timezone, timedelta

from brain_v12.brain.gen_physical_proof import evaluate_physical_proof


class GENPhysicalProofTests(unittest.TestCase):
    def test_missing_evidence_fails_closed(self):
        result = evaluate_physical_proof(None)
        self.assertEqual(result.status, "NOT_PROVEN")
        self.assertFalse(result.accepted)

    def test_simulator_never_proves_hardware(self):
        result = evaluate_physical_proof({"source_type": "SIMULATOR", "simulated_hashrate": 100})
        self.assertEqual(result.status, "SIMULATED")
        self.assertFalse(result.accepted)

    def test_caller_claim_never_proves_hardware(self):
        result = evaluate_physical_proof({
            "source_type": "CALLER_CLAIM",
            "network_connection_verified": True,
            "physical_presence_verified": True,
        })
        self.assertEqual(result.status, "CONNECTED_UNVERIFIED")
        self.assertFalse(result.accepted)

    def test_expired_evidence_is_rejected(self):
        now = datetime(2026, 10, 14, tzinfo=timezone.utc)
        result = evaluate_physical_proof({
            "source_type": "DEVICE_ATTESTATION",
            "observed_at_utc": (now - timedelta(hours=2)).isoformat(),
            "expires_at_utc": (now - timedelta(hours=1)).isoformat(),
        }, now=now)
        self.assertEqual(result.status, "EXPIRED")
        self.assertFalse(result.accepted)

    def test_unverified_trusted_source_fails_closed(self):
        now = datetime(2026, 10, 14, tzinfo=timezone.utc)
        result = evaluate_physical_proof({
            "source_type": "DEVICE_ATTESTATION",
            "subject_type": "ASIC_DEVICE",
            "subject_id": "test-device",
            "evidence_id": "test-evidence",
            "operation": "read_only_diagnostic",
            "verifier_version": "test",
            "observed_at_utc": now.isoformat(),
            "expires_at_utc": (now + timedelta(minutes=5)).isoformat(),
            "challenge_nonce_digest": "digest",
            "result_digest": "digest",
        }, now=now)
        self.assertEqual(result.status, "CHALLENGE_FAILED")
        self.assertFalse(result.accepted)
        self.assertIn("VALID_TRUSTED_SIGNATURE_REQUIRED", result.blocked_reasons)


if __name__ == "__main__":
    unittest.main()
