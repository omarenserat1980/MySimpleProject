"""Tests for the commercial acquisition and delivery evidence loop."""
import unittest

from brain_v12.business.commercial_case import CommercialCase


class CommercialCaseTests(unittest.TestCase):
    def test_case_starts_at_offer_defined(self):
        case = CommercialCase("case-1", "cinematic-factory", "short-film package")
        self.assertEqual(case.stage(), "OFFER_DEFINED")
        self.assertEqual(case.next_evidence_required(), "prospect_evidence")

    def test_case_advances_only_with_evidence(self):
        case = CommercialCase(
            "case-2",
            "customer-portal-api",
            "automation service",
            prospect_evidence="prospect:2",
            customer_evidence="customer:2",
            delivery_evidence="delivery:2",
            payment_evidence="payment:2",
            revenue_evidence="revenue:2",
            cost_evidence="cost:2",
        )
        self.assertEqual(case.stage(), "PROFIT_VERIFIED")
        self.assertEqual(case.next_evidence_required(), "none")

    def test_payment_does_not_equal_profit(self):
        case = CommercialCase(
            "case-3",
            "mining-opportunity-intelligence",
            "analysis report",
            payment_evidence="payment:3",
        )
        self.assertEqual(case.stage(), "PAYMENT_VERIFIED")
        self.assertEqual(case.next_evidence_required(), "revenue_evidence")

    def test_side_effects_are_permission_gated(self):
        record = CommercialCase(
            "case-4", "brain-automation-services", "automation package"
        ).to_record()
        self.assertFalse(record["automatic_outreach"])
        self.assertFalse(record["automatic_contract"])
        self.assertFalse(record["automatic_charge"])
        self.assertFalse(record["automatic_withdrawal"])
        self.assertFalse(record["funds_moved_by_brain"])


if __name__ == "__main__":
    unittest.main()
