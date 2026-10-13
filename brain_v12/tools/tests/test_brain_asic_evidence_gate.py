import hashlib
import hmac
import unittest
from datetime import datetime, timezone

from brain_v12.tools.brain_asic_evidence_gate import canonical_bytes, validate_bundle


class AsicEvidenceGateTests(unittest.TestCase):
    def payload(self):
        return {
            "schema_version": "1.0",
            "evidence_type": "physical_asic",
            "device_id": "test-device-001",
            "device_model": "test-model",
            "transport": "serial",
            "challenge_nonce": "fresh-nonce-for-test",
            "device_response": "challenge-ack-test",
            "test_name": "vendor-safe-self-test",
            "test_result": "PASS",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "raw_evidence_sha256": hashlib.sha256(b"test-only-raw-evidence").hexdigest(),
            "verifier_id": "test-verifier",
        }

    def signed_bundle(self, payload, key=b"test-only-key"):
        signature = hmac.new(key, canonical_bytes(payload), hashlib.sha256).hexdigest()
        return {"payload": payload, "hmac_sha256": signature}, key

    def test_missing_key_is_blocked(self):
        bundle, _ = self.signed_bundle(self.payload())
        result = validate_bundle(bundle, None)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["signature_verified"])

    def test_simulation_cannot_pass_as_physical_hardware(self):
        payload = self.payload()
        payload["evidence_type"] = "software_simulation"
        bundle, key = self.signed_bundle(payload)
        result = validate_bundle(bundle, key)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("physical_asic" in item for item in result["failures"]))

    def test_bad_signature_is_blocked(self):
        bundle, key = self.signed_bundle(self.payload())
        bundle["hmac_sha256"] = "0" * 64
        result = validate_bundle(bundle, key)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["signature_verified"])

    def test_valid_signed_envelope_passes_gate_with_limitations(self):
        bundle, key = self.signed_bundle(self.payload())
        result = validate_bundle(bundle, key)
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["signature_verified"])
        self.assertTrue(result["limitations"])

    def test_stale_evidence_is_blocked(self):
        payload = self.payload()
        payload["observed_at"] = "2020-01-01T00:00:00+00:00"
        bundle, key = self.signed_bundle(payload)
        result = validate_bundle(bundle, key)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("older than 24 hours" in item for item in result["failures"]))


if __name__ == "__main__":
    unittest.main()
