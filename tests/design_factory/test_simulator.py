import unittest

from brain_v12.design_factory.simulator import simulate_step, SIMULATOR_ID


class DesignStepSimulatorTests(unittest.TestCase):
    def test_simulation_is_deterministic_and_explicitly_labeled(self):
        step = {"step_id": "step-01", "domain": "physical_design"}
        first = simulate_step(step)
        second = simulate_step(step)
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "SIMULATED")
        evidence = first["evidence"]
        self.assertEqual(evidence["kind"], "SIMULATION")
        self.assertEqual(evidence["simulator"], SIMULATOR_ID)
        self.assertFalse(evidence["physical_execution"])
        self.assertFalse(evidence["external_side_effects"])
        self.assertEqual(len(evidence["sha256"]), 64)

    def test_simulation_evidence_disclaims_real_world_proof(self):
        result = simulate_step({"step_id": "step-02", "domain": "digital_logic"})
        limits = result["evidence"]["limitations"]
        self.assertIn("not_hardware_evidence", limits)
        self.assertIn("not_manufacturing_evidence", limits)
        self.assertIn("not_mining_evidence", limits)
        self.assertIn("not_revenue_evidence", limits)

    def test_unknown_domain_is_rejected(self):
        with self.assertRaises(ValueError):
            simulate_step({"step_id": "step-03", "domain": "remote_host"})

    def test_missing_step_id_is_rejected(self):
        with self.assertRaises(ValueError):
            simulate_step({"domain": "verification"})


if __name__ == "__main__":
    unittest.main()
