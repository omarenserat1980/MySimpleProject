"""Tests for the simulation-first Brain Phone Base."""
import unittest

from brain_v12.tools.brain_phone_base import (
    REQUIRED_EVIDENCE,
    evaluate_activation_gate,
    simulate_phone_node,
)


class BrainPhoneBaseTests(unittest.TestCase):
    def test_simulation_is_explicit_and_never_claims_real_device(self):
        result = simulate_phone_node()
        self.assertEqual(result["mode"], "SIMULATOR")
        self.assertTrue(result["synthetic"])
        self.assertFalse(result["real_device_connected"])
        self.assertFalse(result["real_activation_performed"])
        self.assertFalse(result["tasks_dispatched"])
        self.assertFalse(result["mining_started"])
        self.assertFalse(result["revenue_verified"])

    def test_invalid_node_id_rejected(self):
        with self.assertRaises(ValueError):
            simulate_phone_node(" ")

    def test_empty_evidence_fails_closed(self):
        result = evaluate_activation_gate({})
        self.assertEqual(result["state"], "BLOCKED")
        self.assertEqual(set(result["missing_evidence"]), set(REQUIRED_EVIDENCE))
        self.assertFalse(result["automatic_activation_allowed"])

    def test_self_reported_evidence_is_not_accepted(self):
        evidence = {
            key: {"verified": True, "source": "self_reported", "digest": "a" * 64}
            for key in REQUIRED_EVIDENCE
        }
        result = evaluate_activation_gate(evidence)
        self.assertEqual(result["state"], "BLOCKED")
        self.assertEqual(set(result["missing_evidence"]), set(REQUIRED_EVIDENCE))

    def test_complete_evidence_only_allows_manual_review(self):
        evidence = {
            key: {"verified": True, "source": "trusted-verifier", "digest": "a" * 64}
            for key in REQUIRED_EVIDENCE
        }
        result = evaluate_activation_gate(evidence)
        self.assertEqual(result["state"], "ELIGIBLE_FOR_MANUAL_REVIEW")
        self.assertFalse(result["real_activation_performed"])
        self.assertFalse(result["automatic_activation_allowed"])
        self.assertFalse(result["tasks_dispatched"])
        self.assertFalse(result["mining_started"])


if __name__ == "__main__":
    unittest.main()
