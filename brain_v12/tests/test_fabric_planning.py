import unittest

from brain_v12.brain.device_cloud_federation import eligible_fabric_resources


class FabricPlanningTests(unittest.TestCase):
    def test_virtual_record_requires_simulation_claim(self):
        record = {
            "resource_id": "virtual-plan-01",
            "reality_mode": "VIRTUAL",
            "capabilities": ["cpu"],
        }
        result = eligible_fabric_resources({"resources": [record]}, {"cpu"})
        self.assertEqual(result["status"], "NO_ELIGIBLE_RESOURCE")
        self.assertEqual(result["eligible"], [])

    def test_virtual_simulation_record_is_plannable(self):
        record = {
            "resource_id": "virtual-plan-02",
            "reality_mode": "VIRTUAL",
            "capabilities": ["cpu", "simulation"],
            "execution_claim": "SIMULATION_ONLY",
        }
        result = eligible_fabric_resources({"resources": [record]}, {"cpu"})
        self.assertEqual(result["status"], "ELIGIBLE")
        self.assertEqual(result["eligible"], [record])

    def test_capability_filter_rejects_mismatch(self):
        record = {
            "resource_id": "virtual-plan-03",
            "reality_mode": "VIRTUAL",
            "capabilities": ["cpu"],
            "execution_claim": "SIMULATION_ONLY",
        }
        result = eligible_fabric_resources({"resources": [record]}, {"gpu"})
        self.assertEqual(result["status"], "NO_ELIGIBLE_RESOURCE")
        self.assertIn("CAPABILITY_MISMATCH", result["rejected"][0]["reasons"])


if __name__ == "__main__":
    unittest.main()
