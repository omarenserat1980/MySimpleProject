"""Regression tests for Bitcoin Mining Intelligence's safety and accounting contract."""
import unittest

from brain_v12.brain.bitcoin_mining_intelligence_api import (
    MiningAnalysisRequest,
    bitcoin_mining_analyze,
    bitcoin_mining_plan,
    bitcoin_mining_status,
)


class BitcoinMiningIntelligenceTests(unittest.TestCase):
    def test_status_is_analysis_only_and_zero_capital(self):
        result = bitcoin_mining_status()
        self.assertEqual(result["capital_budget_jod"], 0)
        self.assertFalse(result["real_mining_enabled"])
        self.assertFalse(result["wallet_access"])
        self.assertEqual(result["verified_revenue_jod"], 0.0)

    def test_analysis_marks_revenue_unverified(self):
        result = bitcoin_mining_analyze(MiningAnalysisRequest(
            algorithm="SHA-256",
            hashrate=100,
            hashrate_unit="TH",
            power_watts=3000,
            electricity_jod_per_kwh=0.0,
            gross_revenue_jod_per_day=1.0,
        ))
        self.assertEqual(result["revenue_verification"], "UNVERIFIED")
        self.assertFalse(result["live_market_data"])
        self.assertFalse(result["intelligence"]["execution_authorized"])

    def test_plan_never_starts_real_mining(self):
        result = bitcoin_mining_plan(MiningAnalysisRequest(
            algorithm="SHA-256",
            hashrate=100,
            hashrate_unit="TH",
            power_watts=0,
            electricity_jod_per_kwh=0.0,
            gross_revenue_jod_per_day=1.0,
        ))
        self.assertEqual(result["mode"], "DRY_RUN")
        self.assertEqual(result["status"], "BLOCKED_REVENUE_UNVERIFIED")
        self.assertFalse(result["profit_gate"] if "profit_gate" in result else False)
        self.assertFalse(result["real_mining_started"])
        self.assertFalse(result["spend_authorized"])
        self.assertEqual(result["verified_revenue_jod"], 0.0)
        self.assertEqual(result["stages"][-1]["status"], "NOT_ESTABLISHED")

    def test_nonzero_other_cost_blocks_zero_capital_gate(self):
        result = bitcoin_mining_plan(MiningAnalysisRequest(
            algorithm="SHA-256",
            hashrate=1,
            hashrate_unit="TH",
            power_watts=0,
            electricity_jod_per_kwh=0.0,
            gross_revenue_jod_per_day=1.0,
            other_daily_cost_jod=0.01,
        ))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["stages"][2]["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
