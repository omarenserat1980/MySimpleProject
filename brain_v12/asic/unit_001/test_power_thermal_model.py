import unittest

from brain_v12.asic.unit_001.power_thermal_model import (
    ModelInputError, ModelParams, simulate_step, simulate_profile
)


class PowerThermalModelTests(unittest.TestCase):
    def test_outputs_are_explicitly_simulated(self):
        result = simulate_step(0.5, 10)
        self.assertTrue(result["simulated"])
        self.assertFalse(result["calibrated_to_real_device"])
        self.assertEqual(result["evidence_class"], "MODEL")

    def test_power_and_current_increase_with_workload(self):
        low = simulate_step(0.1, 60)["outputs"]
        high = simulate_step(1.0, 60)["outputs"]
        self.assertGreater(high["chip_power_w"], low["chip_power_w"])
        self.assertGreater(high["input_current_a"], low["input_current_a"])

    def test_temperature_moves_toward_steady_state(self):
        p = ModelParams()
        result = simulate_step(1.0, 30, p.ambient_temp_c, p)["outputs"]
        self.assertGreater(result["estimated_temp_c"], p.ambient_temp_c)
        self.assertLess(result["estimated_temp_c"], result["steady_state_temp_c"])

    def test_long_time_approaches_steady_state(self):
        result = simulate_step(1.0, 100000)["outputs"]
        self.assertAlmostEqual(result["estimated_temp_c"],
                               result["steady_state_temp_c"], places=3)

    def test_profile_carries_temperature_forward(self):
        results = simulate_profile([
            {"utilization": 0.2, "duration_s": 30},
            {"utilization": 0.9, "duration_s": 30},
        ])
        self.assertEqual(len(results), 2)
        self.assertGreater(results[1]["outputs"]["estimated_temp_c"],
                           results[0]["outputs"]["estimated_temp_c"])

    def test_rejects_bad_utilization_and_duration(self):
        with self.assertRaises(ModelInputError):
            simulate_step(1.1, 10)
        with self.assertRaises(ModelInputError):
            simulate_step(0.5, 0)

    def test_rejects_efficiency_above_one(self):
        with self.assertRaises(ModelInputError):
            simulate_step(0.5, 10, params=ModelParams(conversion_efficiency=1.2))


if __name__ == "__main__":
    unittest.main()
