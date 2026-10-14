import unittest
from brain_v12.design_factory.brain_adapter import DesignFactoryAdapter, TOOL_CATALOG_ITEM

class BrainAdapterTests(unittest.TestCase):
    def setUp(self):
        self.adapter = DesignFactoryAdapter()

    def test_catalog_declares_low_risk_plan_only_tool(self):
        self.assertEqual(TOOL_CATALOG_ITEM["id"], "design.plan")
        self.assertEqual(TOOL_CATALOG_ITEM["risk"], "low")
        self.assertEqual(TOOL_CATALOG_ITEM["execution_mode"], "plan_only")

    def test_adapter_returns_plan_without_execution(self):
        result = self.adapter.execute({"task": "Bitcoin ASIC RTL and OpenROAD physical design"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "PLANNED")
        self.assertFalse(result["execution_started"])
        self.assertEqual(result["data"]["status"], "PLANNED")
        self.assertIn("G7_PHYSICAL", result["data"]["required_gates"])

    def test_missing_task_fails_closed(self):
        result = self.adapter.execute({})
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["error"], "TASK_DESCRIPTION_REQUIRED")

if __name__ == "__main__":
    unittest.main()
