import unittest

from brain_v12.brain.linux_simulator import evaluate_linux_simulation


class LinuxSimulatorTests(unittest.TestCase):
    def test_default_profile_passes_only_as_simulation(self):
        result = evaluate_linux_simulation()
        self.assertEqual(result["simulation_status"], "SIMULATION_PASS")
        self.assertEqual(result["fidelity"], "SIMULATED")
        self.assertFalse(result["host_capacity_verified"])
        self.assertFalse(result["native_linux_running"])
        self.assertFalse(result["qemu_started"])
        self.assertFalse(result["real_execution_authorized"])
        self.assertFalse(result["windows_boot_verified"])
        self.assertFalse(result["side_effects_performed"])

    def test_invalid_profile_is_blocked(self):
        result = evaluate_linux_simulation({
            "name": "", "architecture": "arm64", "vcpus": 0,
            "memory_mib": 64, "disk_gib": 0, "qemu_expected": False,
        })
        self.assertEqual(result["simulation_status"], "SIMULATION_BLOCKED")
        self.assertIn("PROFILE_NAME_FAILED", result["blockers"])
        self.assertIn("ARCHITECTURE_SUPPORTED_BY_MODEL_FAILED", result["blockers"])
        self.assertIn("QEMU_MODELED_AVAILABLE_FAILED", result["blockers"])
        self.assertFalse(result["real_execution_authorized"])

    def test_simulated_kvm_does_not_claim_real_kvm_access(self):
        result = evaluate_linux_simulation({"kvm_expected": True})
        self.assertTrue(result["checks"]["kvm_modeled_available"])
        self.assertFalse(result["kvm_access_verified"])
        self.assertFalse(result["host_capacity_verified"])

    def test_malformed_resource_values_fail_closed(self):
        result = evaluate_linux_simulation({"vcpus": "many", "memory_mib": None})
        self.assertEqual(result["simulation_status"], "SIMULATION_BLOCKED")
        self.assertFalse(result["real_execution_authorized"])


if __name__ == "__main__":
    unittest.main()
