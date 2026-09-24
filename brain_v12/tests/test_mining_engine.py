import unittest

from brain_v12.brain.mining_engine import MiningEngine


class MiningEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = MiningEngine()

    def test_energy_cost_and_net_profit(self):
        result = self.engine.analyze({
            "algorithm": "test",
            "hashrate": 100,
            "hashrate_unit": "MH",
            "power_watts": 1000,
            "electricity_jod_per_kwh": 0.10,
            "gross_revenue_jod_per_day": 5,
            "hardware_cost_jod": 500,
            "pool_fee_percent": 2,
            "other_daily_cost_jod": 0.5,
        })
        self.assertEqual(result["energy_kwh_per_day"], 24.0)
        self.assertEqual(result["electricity_jod_per_day"], 2.4)
        self.assertEqual(result["pool_fee_jod_per_day"], 0.1)
        self.assertEqual(result["net_jod_per_day"], 2.0)
        self.assertEqual(result["break_even_days"], 250.0)
        self.assertEqual(result["revenue_verification"], "UNVERIFIED")

    def test_invalid_unit_is_rejected(self):
        with self.assertRaises(ValueError):
            self.engine.normalize_hashrate(1, "INVALID")

    def test_compare_is_explicitly_input_based(self):
        result = self.engine.compare([
            {
                "algorithm": "A",
                "hashrate": 1,
                "hashrate_unit": "TH",
                "power_watts": 100,
                "electricity_jod_per_kwh": 0.1,
                "gross_revenue_jod_per_day": 1,
            },
            {
                "algorithm": "B",
                "hashrate": 1,
                "hashrate_unit": "TH",
                "power_watts": 100,
                "electricity_jod_per_kwh": 0.1,
                "gross_revenue_jod_per_day": 3,
            },
        ])
        self.assertEqual(result["order"], ["B", "A"])
        self.assertEqual(result["ranking_basis"], "net_jod_per_day_from_supplied_inputs")
        self.assertIn("not", result["warning"].lower())

    def test_snapshot_does_not_claim_live_mining(self):
        snapshot = self.engine.snapshot()
        self.assertFalse(snapshot["live_data_connected"])
        self.assertEqual(snapshot["execution"], "ANALYSIS_ONLY")
        self.assertEqual(snapshot["verified_revenue_jod"], 0.0)


if __name__ == "__main__":
    unittest.main()
