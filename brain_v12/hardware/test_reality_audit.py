"""Tests for the hardware reality registry validator."""
import unittest

from brain_v12.hardware.reality_audit import audit_registry


def valid_registry():
    return {
        "schema_version": 1,
        "audit_policy": {"never_infer_physical_hardware_from_simulation": True},
        "components": [{
            "id": "ram", "name": "RAM", "reality_status": "ADAPTER_IMPLEMENTED",
            "evidence": ["adapter file"], "not_proven": ["physical RAM"],
            "next_gate": "run upstream simulator",
        }],
    }


class RealityAuditTests(unittest.TestCase):
    def test_valid_registry_passes_structural_audit(self):
        result = audit_registry(valid_registry())
        self.assertTrue(result["passed"])
        self.assertEqual(result["component_count"], 1)
        self.assertIn("no external evidence", result["claim_boundary"])

    def test_duplicate_component_ids_fail(self):
        data = valid_registry()
        data["components"].append(dict(data["components"][0]))
        result = audit_registry(data)
        self.assertFalse(result["passed"])
        self.assertTrue(any("duplicate component id" in e for e in result["errors"]))

    def test_unknown_status_fails(self):
        data = valid_registry()
        data["components"][0]["reality_status"] = "REAL_TRUST_ME"
        self.assertFalse(audit_registry(data)["passed"])

    def test_physical_claim_without_independent_verifier_fails(self):
        data = valid_registry()
        data["components"][0]["reality_status"] = "PHYSICAL_HARDWARE_VERIFIED"
        self.assertFalse(audit_registry(data)["passed"])

    def test_policy_must_fail_closed(self):
        data = valid_registry()
        data["audit_policy"]["never_infer_physical_hardware_from_simulation"] = False
        self.assertFalse(audit_registry(data)["passed"])


if __name__ == "__main__":
    unittest.main()
