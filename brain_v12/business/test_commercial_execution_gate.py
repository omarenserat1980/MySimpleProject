import unittest

from brain_v12.business.commercial_execution_gate import (
    CommercialFundingEvidence,
    evaluate_paid_execution,
)


class CommercialExecutionGateTests(unittest.TestCase):
    def test_default_is_fail_closed(self):
        result = evaluate_paid_execution(CommercialFundingEvidence())
        self.assertFalse(result.paid_allowed)

    def test_requires_authorization(self):
        result = evaluate_paid_execution(
            CommercialFundingEvidence(
                available_funds_verified=True,
                available_amount=100,
                evidence_refs=["funds:1"],
            )
        )
        self.assertFalse(result.paid_allowed)
        self.assertEqual(result.reason, "EXPLICIT_AUTHORIZATION_REQUIRED")

    def test_requires_verified_positive_funds_and_evidence(self):
        result = evaluate_paid_execution(
            CommercialFundingEvidence(
                authorized=True,
                available_funds_verified=True,
                available_amount=0,
                evidence_refs=["funds:1"],
            )
        )
        self.assertFalse(result.paid_allowed)

    def test_enables_paid_mode_only_with_all_gates(self):
        result = evaluate_paid_execution(
            CommercialFundingEvidence(
                authorized=True,
                available_funds_verified=True,
                available_amount=100,
                currency="USD",
                evidence_refs=["funds:verified-statement"],
            )
        )
        self.assertTrue(result.paid_allowed)
        self.assertEqual(result.reason, "COMMERCIAL_MODE_ENABLED")


if __name__ == "__main__":
    unittest.main()
