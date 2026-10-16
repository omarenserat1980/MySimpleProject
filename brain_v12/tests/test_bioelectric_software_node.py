import math
import unittest

from brain_v12.brain.bioelectric_software_node import simulate_bioelectric_node


class BioelectricSoftwareNodeTests(unittest.TestCase):
    def test_default_is_explicitly_simulation_not_real_generation(self):
        result = simulate_bioelectric_node()
        self.assertEqual(result.status, "SIMULATED_ONLY")
        self.assertEqual(result.evidence_class, "MODEL_ESTIMATE")
        self.assertFalse(result.real_electricity_verified)
        self.assertFalse(result.revenue_verified)
        self.assertGreater(result.open_circuit_voltage_v, 0)
        self.assertGreater(result.load_power_w, 0)

    def test_series_cells_increase_open_circuit_voltage(self):
        one = simulate_bioelectric_node(cells_in_series=1, parallel_strings=1)
        many = simulate_bioelectric_node(cells_in_series=10, parallel_strings=1)
        self.assertAlmostEqual(many.open_circuit_voltage_v, one.open_circuit_voltage_v * 10)

    def test_parallel_strings_reduce_equivalent_internal_resistance(self):
        one = simulate_bioelectric_node(parallel_strings=1)
        many = simulate_bioelectric_node(parallel_strings=5)
        self.assertAlmostEqual(
            many.equivalent_internal_resistance_ohm,
            one.equivalent_internal_resistance_ohm / 5,
        )

    def test_zero_pulse_rate_means_zero_modeled_average_power(self):
        result = simulate_bioelectric_node(pulses_per_second=0)
        self.assertEqual(result.modeled_average_power_w, 0)
        self.assertGreater(result.energy_per_pulse_j, 0)

    def test_rejects_invalid_electrical_parameters(self):
        for kwargs in (
            {"cells_in_series": 0},
            {"parallel_strings": -1},
            {"cell_voltage_v": 0},
            {"cell_internal_resistance_ohm": -1},
            {"load_resistance_ohm": 0},
            {"pulse_duration_s": 0},
            {"pulses_per_second": -1},
            {"cell_voltage_v": math.inf},
            {"pulse_duration_s": 1e308, "pulses_per_second": 1e308},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                simulate_bioelectric_node(**kwargs)

    def test_model_never_promotes_estimate_to_real_evidence(self):
        result = simulate_bioelectric_node(
            cells_in_series=10000,
            parallel_strings=10000,
            cell_voltage_v=10,
            cell_internal_resistance_ohm=0,
            load_resistance_ohm=0.01,
            pulse_duration_s=100,
            pulses_per_second=100,
        )
        self.assertEqual(result.status, "SIMULATED_ONLY")
        self.assertFalse(result.real_electricity_verified)
        self.assertFalse(result.revenue_verified)
        self.assertTrue(result.notes)


if __name__ == "__main__":
    unittest.main()
