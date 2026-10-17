"""Regression tests for Bitcoin Mining Intelligence's safety and accounting contract."""
import os
import unittest
from unittest.mock import patch

from brain_v12.brain.bitcoin_mining_intelligence_api import (
    MiningAnalysisRequest,
    bitcoin_mining_analyze,
    bitcoin_mining_plan,
    bitcoin_mining_status,
    HashBenchmarkRequest,
    bitcoin_mining_benchmark,
    router,
)


class BitcoinMiningIntelligenceTests(unittest.TestCase):
    def test_status_is_analysis_only_and_zero_capital(self):
        result = bitcoin_mining_status()
        self.assertEqual(result["capital_budget_jod"], 0)
        self.assertFalse(result["real_mining_enabled"])
        self.assertFalse(result["wallet_access"])
        self.assertEqual(result["verified_revenue_jod"], 0.0)

    def test_zero_budget_is_a_default_not_a_permanent_ceiling(self):
        with patch.dict(os.environ, {"BRAIN_CAPITAL_BUDGET_JOD": "12.5", "BRAIN_ALLOW_PAID_MINING": "1"}):
            result = bitcoin_mining_status()
        self.assertEqual(result["capital_budget_jod"], 12.5)
        self.assertTrue(result["paid_cloud_mining_allowed"])
        self.assertIn("maximize verified net income", result["income_objective"])
        # Configuring a budget still does not fabricate a real ASIC adapter.
        self.assertFalse(result["real_mining_enabled"])
        self.assertEqual(result["real_mining_blocker"], "NO_VERIFIED_PHYSICAL_MINING_ADAPTER")

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
        self.assertEqual(result["profit_gate"]["status"], "BLOCKED_REVENUE_UNVERIFIED")
        self.assertFalse(result["profit_gate"]["execution_authorized"])
        self.assertFalse(result["real_mining_started"])
        self.assertFalse(result["spend_authorized"])
        self.assertEqual(result["verified_revenue_jod"], 0.0)
        self.assertEqual(result["stages"][-1]["status"], "NOT_ESTABLISHED")

    def test_operating_cost_is_accounted_but_is_not_upfront_capital(self):
        result = bitcoin_mining_plan(MiningAnalysisRequest(
            algorithm="SHA-256",
            hashrate=1,
            hashrate_unit="TH",
            power_watts=0,
            electricity_jod_per_kwh=0.0,
            gross_revenue_jod_per_day=1.0,
            other_daily_cost_jod=0.01,
        ))
        self.assertEqual(result["status"], "BLOCKED_REVENUE_UNVERIFIED")
        self.assertEqual(result["stages"][2]["status"], "PASS")
        self.assertGreater(result["analysis"]["other_cost_jod_per_day"], 0)


    def test_local_hash_benchmark_is_bounded_and_not_real_mining(self):
        result = bitcoin_mining_benchmark(HashBenchmarkRequest(
            duration_seconds=0.05, max_hashes=100,
        ))
        self.assertTrue(result["ok"])
        self.assertEqual(result["mode"], "LOCAL_BENCHMARK_ONLY")
        self.assertGreater(result["hashes_completed"], 0)
        self.assertFalse(result["pool_connected"])
        self.assertFalse(result["real_bitcoin_mining"])
        self.assertFalse(result["revenue_verified"])


    def test_status_http_route_is_bound_to_status_payload_not_budget_helper(self):
        status_routes = [
            route for route in router.routes
            if getattr(route, "path", None) == "/api/bitcoin-mining/status"
            and "GET" in (getattr(route, "methods", set()) or set())
        ]
        self.assertEqual(len(status_routes), 1)
        self.assertEqual(status_routes[0].path, "/api/bitcoin-mining/status")
        self.assertIs(status_routes[0].endpoint, bitcoin_mining_status)
        payload = status_routes[0].endpoint()
        self.assertEqual(payload["execution_mode"], "ANALYSIS_AND_DRY_RUN_ONLY")
        self.assertFalse(payload["real_mining_enabled"])
        self.assertEqual(payload["verified_revenue_jod"], 0.0)


if __name__ == "__main__":
    unittest.main()
