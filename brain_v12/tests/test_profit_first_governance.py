import unittest

from brain_v12.brain.profit_first_governance import (
    ProfitInputs,
    audit_profit_blockers,
    evaluate_profit,
    income_plan,
)


class ProfitFirstGovernanceTests(unittest.TestCase):
    def test_zero_budget_is_not_a_permanent_income_ceiling(self):
        plan = income_plan(0, 1_000_000)
        self.assertEqual(plan["current_budget"], 0)
        self.assertEqual(plan["target_budget"], 1_000_000)
        self.assertEqual(plan["remaining_gap"], 1_000_000)
        self.assertEqual(plan["guaranteed_income"], 0)

    def test_positive_profit_does_not_claim_execution_without_authorization(self):
        result = evaluate_profit(ProfitInputs(
            expected_gross_revenue_per_day=10,
            electricity_cost_per_day=2,
            inputs_verified=True,
            device_connected=True,
            pool_authorized=True,
            payout_destination_configured=True,
            hardware_safe=True,
            explicit_execution_authorization=False,
        ))
        self.assertEqual(result["status"], "PROFITABLE_ESTIMATE")
        self.assertFalse(result["execution_ready"])
        self.assertIn("EXPLICIT_EXECUTION_AUTHORIZATION_REQUIRED", result["blockers"])

    def test_unverified_estimate_never_becomes_verified_profit(self):
        result = evaluate_profit(ProfitInputs(
            expected_gross_revenue_per_day=10,
            electricity_cost_per_day=2,
        ))
        self.assertEqual(result["status"], "UNVERIFIED_ESTIMATE")
        self.assertIn("UNVERIFIED_PROFIT_INPUTS", result["blockers"])
        self.assertFalse(result["execution_ready"])

    def test_negative_profit_is_rejected(self):
        result = evaluate_profit(ProfitInputs(
            expected_gross_revenue_per_day=1,
            electricity_cost_per_day=2,
            inputs_verified=True,
            device_connected=True,
            pool_authorized=True,
            payout_destination_configured=True,
            hardware_safe=True,
            explicit_execution_authorization=True,
        ))
        self.assertEqual(result["status"], "NOT_PROFITABLE")
        self.assertIn("NON_POSITIVE_NET_PROFIT", result["blockers"])
        self.assertFalse(result["execution_ready"])

    def test_blocker_audit_flags_missing_real_mining_path(self):
        result = audit_profit_blockers({
            "revenue_goal_configured": True,
            "profitability_gate_enabled": True,
            "real_mining_adapter_available": False,
            "pool_connection_verified": False,
            "payout_evidence_available": False,
            "free_opportunity_scan_enabled": True,
        })
        codes = {item["code"] for item in result["findings"]}
        self.assertIn("NO_REAL_MINING_ADAPTER", codes)
        self.assertIn("POOL_CONNECTION_UNVERIFIED", codes)
        self.assertIn("NO_PAYOUT_EVIDENCE", codes)
        self.assertTrue(result["never_suppress"])


if __name__ == "__main__":
    unittest.main()
