"""Fail-closed tests for the phone evidence verification gate."""
import unittest
from unittest.mock import patch

from brain_v12.tools.brain_phone_readonly_inspector import inspect_local_resources
from brain_v12.tools.brain_phone_verification_gate import validate_phone_evidence


class PhoneVerificationGateTests(unittest.TestCase):
    def evidence(self):
        with patch("brain_v12.tools.brain_phone_readonly_inspector.collect_resource_snapshot") as collect:
            collect.return_value = {
                "observed_at_utc": "2026-10-15T16:00:00+00:00",
                "os": "Linux", "os_release": "test", "architecture": "aarch64",
                "python_version": "3.x", "cpu_logical_count": 8,
                "available_memory_bytes": 1024,
                "disk": {"total_bytes": 4096, "free_bytes": 2048},
                "load_average_1_5_15": None,
            }
            return inspect_local_resources("test-phone")

    def test_valid_structure_never_means_independently_verified(self):
        result = validate_phone_evidence(self.evidence())
        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(result["trust_state"], "UNTRUSTED")
        self.assertFalse(result["independent_verification"])
        self.assertFalse(result["eligible_for_activation"])
        self.assertFalse(result["eligible_for_mining"])

    def test_missing_safety_flag_fails_closed(self):
        evidence = self.evidence()
        del evidence["mining_started"]
        result = validate_phone_evidence(evidence)
        self.assertFalse(result["valid"])
        self.assertIn("SAFETY_FLAG_NOT_FALSE:mining_started", result["errors"])

    def test_claimed_identity_verification_is_rejected(self):
        evidence = self.evidence()
        evidence["device_identity_verified"] = True
        result = validate_phone_evidence(evidence)
        self.assertFalse(result["valid"])
        self.assertIn("SAFETY_FLAG_NOT_FALSE:device_identity_verified", result["errors"])

    def test_bad_resource_values_are_rejected(self):
        evidence = self.evidence()
        evidence["resources"]["cpu_logical_count"] = -3
        result = validate_phone_evidence(evidence)
        self.assertFalse(result["valid"])
        self.assertIn("INVALID_RESOURCE:cpu_logical_count", result["errors"])

    def test_non_object_payload_fails_closed(self):
        result = validate_phone_evidence(["not", "an", "object"])
        self.assertFalse(result["valid"])
        self.assertEqual(result["trust_state"], "UNTRUSTED")


if __name__ == "__main__":
    unittest.main()
