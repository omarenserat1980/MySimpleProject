import unittest

from brain_v12.brain.azure_vm_simulator import AzureVmSpec, simulate_vm


class AzureVmSimulatorTests(unittest.TestCase):
    def test_default_plan_is_simulated_and_not_a_real_boot(self):
        result = simulate_vm()
        self.assertEqual(result["status"], "SIMULATED_PLAN_READY")
        self.assertTrue(result["simulation"])
        self.assertFalse(result["azure_api_called"])
        self.assertFalse(result["resource_created"])
        self.assertFalse(result["real_boot_verified"])
        self.assertIsNone(result["boot_evidence"])
        self.assertEqual(result["cloud"], "alexa")

    def test_wrong_cloud_is_blocked(self):
        result = simulate_vm(AzureVmSpec(cloud_name="arkan"))
        self.assertEqual(result["status"], "SIMULATED_PLAN_BLOCKED")
        self.assertFalse(result["checks"]["cloud_name_is_alexa"])
        self.assertFalse(result["real_boot_verified"])

    def test_wrong_image_is_blocked(self):
        result = simulate_vm(AzureVmSpec(image="Ubuntu:latest"))
        self.assertEqual(result["status"], "SIMULATED_PLAN_BLOCKED")
        self.assertFalse(result["checks"]["windows_server_2025_image"])

    def test_undersized_disk_is_blocked(self):
        result = simulate_vm(AzureVmSpec(os_disk_gib=32))
        self.assertEqual(result["status"], "SIMULATED_PLAN_BLOCKED")
        self.assertFalse(result["checks"]["disk_capacity_positive"])


if __name__ == "__main__":
    unittest.main()
