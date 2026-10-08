import unittest
from brain_v12.brain.zero_capital_gate import ZeroCapitalGate


class ZeroCapitalGateTests(unittest.TestCase):
    def test_zero_cost_is_eligible(self):
        r = ZeroCapitalGate.evaluate({"title": "Arabic content service", "cost": 0, "expected_jod": 25})
        self.assertTrue(r.eligible)
        self.assertEqual(r.capital_required_jod, 0)

    def test_paid_cloud_is_rejected(self):
        r = ZeroCapitalGate.evaluate({"title": "Cloud mining contract", "requirements": "paid cloud subscription", "cost": 0})
        self.assertFalse(r.eligible)
        self.assertEqual(r.reason, "CAPITAL_OR_PAYMENT_REQUIRED")

    def test_nonzero_direct_cost_is_rejected(self):
        r = ZeroCapitalGate.evaluate({"title": "GPU mining", "direct_cost_jod": 2, "expected_revenue_jod": 5})
        self.assertFalse(r.eligible)
        self.assertEqual(r.reason, "NONZERO_CAPITAL_REQUIRED")

    def test_negative_cost_cannot_create_fake_eligibility(self):
        r = ZeroCapitalGate.evaluate({"title": "Free task", "direct_cost_jod": -100, "expected_jod": 10})
        self.assertTrue(r.eligible)
        self.assertEqual(r.direct_cost_jod, 0)

    def test_filter_keeps_only_zero_capital_items(self):
        rows = ZeroCapitalGate.filter([
            {"title": "Free service", "cost": 0},
            {"title": "Paid service", "cost": 1},
        ])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Free service")


if __name__ == "__main__":
    unittest.main()
