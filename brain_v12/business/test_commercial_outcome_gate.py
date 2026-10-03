"""Tests for the commercial outcome gate."""
import unittest

from brain_v12.business.commercial_outcome_gate import (
    CommercialOutcome,
    evaluate_commercial_outcome,
)


class CommercialOutcomeGateTests(unittest.TestCase):
    def test_engineering_success_does_not_equal_revenue(self):
        result = evaluate_commercial_outcome(
            CommercialOutcome(
                capability_id="cinematic-factory",
                monetization_path="customer-paid-film",
            )
        )
        self.assertEqual(result["status"], "MONETIZATION_PATH_DEFINED")
        self.assertTrue(result["engineering_green_is_not_revenue"])

    def test_verified_payment_marks_revenue_path_progress(self):
        result = evaluate_commercial_outcome(
            CommercialOutcome(
                capability_id="mining-intelligence",
                monetization_path="paid-analysis",
                customer_or_buyer_evidence=True,
                payment_verified=True,
            )
        )
        self.assertEqual(result["status"], "PAYMENT_VERIFIED")
        self.assertTrue(result["revenue_success_requires_verified_payment"])

    def test_realized_revenue_requires_payment_and_amount(self):
        with self.assertRaises(ValueError):
            evaluate_commercial_outcome(
                CommercialOutcome(
                    capability_id="api",
                    monetization_path="subscription",
                    revenue_realized=True,
                )
            )

    def test_profit_requires_verified_costs(self):
        with self.assertRaises(ValueError):
            evaluate_commercial_outcome(
                CommercialOutcome(
                    capability_id="api",
                    monetization_path="subscription",
                    payment_verified=True,
                    revenue_realized=True,
                    realized_amount=100.0,
                    profit_verified=True,
                )
            )

    def test_profit_verified_is_terminal_commercial_success(self):
        result = evaluate_commercial_outcome(
            CommercialOutcome(
                capability_id="api",
                monetization_path="subscription",
                payment_verified=True,
                revenue_realized=True,
                realized_amount=100.0,
                costs_verified=20.0,
                profit_verified=True,
                evidence_refs=["payment:tx-1", "cost:ledger-1"],
            )
        )
        self.assertEqual(result["status"], "PROFIT_VERIFIED")
        self.assertFalse(result["automatic_withdrawal"])


if __name__ == "__main__":
    unittest.main()
