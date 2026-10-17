import unittest

from brain_v12.asic.unit_001.board_simulator import (
    MODEL_ID,
    known_answer_test,
    simulate_board,
)


class BoardSimulatorTests(unittest.TestCase):
    def test_sha256d_known_answer_vector(self):
        result = known_answer_test()
        self.assertTrue(result["passed"])
        self.assertEqual(result["expected_digest_hex"], result["actual_digest_hex"])

    def test_simulation_never_claims_physical_hardware(self):
        report = simulate_board()
        self.assertTrue(report["simulation_only"])
        self.assertFalse(report["physical_hardware_access"])
        self.assertEqual(report["board_presence"], "NOT_VERIFIED")
        self.assertEqual(report["chip_presence"], "NOT_VERIFIED")
        self.assertEqual(report["mining_status"], "NOT_RUN")
        self.assertIsNone(report["measured_hashrate_hs"])
        self.assertIsNone(report["measured_power_watts"])
        self.assertIsNone(report["accepted_pool_shares"])
        self.assertEqual(report["model_id"], MODEL_ID)

    def test_all_synthetic_telemetry_is_labeled_simulated(self):
        telemetry = simulate_board()["simulated_telemetry"]
        for value in telemetry.values():
            if isinstance(value, str) and value not in {"These are model states, not physical measurements."}:
                self.assertIn("SIMULATED", value)


if __name__ == "__main__":
    unittest.main()
