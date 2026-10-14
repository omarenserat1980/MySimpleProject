import unittest
from brain_v12.design_factory.brain_adapter import DesignFactoryAdapter, TOOL_CATALOG_ITEM


class BrainAdapterTests(unittest.TestCase):
    def setUp(self):
        self.adapter = DesignFactoryAdapter()

    def test_catalog_declares_low_risk_plan_only_tool(self):
        self.assertEqual(TOOL_CATALOG_ITEM["id"], "design.plan")
        self.assertEqual(TOOL_CATALOG_ITEM["risk"], "low")
        self.assertEqual(TOOL_CATALOG_ITEM["execution_mode"], "plan_only")

    def test_adapter_returns_plan_and_initialized_ledger_without_execution(self):
        result = self.adapter.execute({"task": "Bitcoin ASIC RTL and OpenROAD physical design"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "PLANNED")
        self.assertFalse(result["execution_started"])
        self.assertEqual(result["data"]["status"], "PLANNED")
        self.assertIn("G7_PHYSICAL", result["data"]["required_gates"])
        self.assertEqual(result["execution_ledger"]["status"], "PLANNED")
        self.assertFalse(result["execution_ledger"]["execution_started"])
        self.assertGreater(len(result["execution_ledger"]["steps"]), 0)

    def test_missing_task_fails_closed(self):
        result = self.adapter.execute({})
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["error"], "TASK_DESCRIPTION_REQUIRED")

    def test_step_mode_advances_only_plan_ledger_by_default(self):
        planned = self.adapter.execute({"task": "Bitcoin ASIC RTL and OpenROAD physical design"})
        result = self.adapter.execute({
            "mode": "step",
            "execution_ledger": planned["execution_ledger"],
        })
        self.assertTrue(result["ok"])
        self.assertEqual(result["execution_ledger"]["steps"][0]["status"], "PLANNED")
        self.assertEqual(result["execution_ledger"]["next_step_index"], 0)
        self.assertFalse(result["execution_started"])

    def test_step_mode_without_ledger_is_blocked(self):
        result = self.adapter.execute({"mode": "step"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["error"], "EXECUTION_LEDGER_REQUIRED")

    def test_step_mode_cannot_execute_without_configured_executor(self):
        planned = self.adapter.execute({"task": "Bitcoin ASIC RTL and OpenROAD physical design"})
        result = self.adapter.execute({
            "mode": "step",
            "execution_ledger": planned["execution_ledger"],
            "authorize": True,
            "dry_run": False,
        })
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(
            result["execution_ledger"]["steps"][0]["evidence"]["reason"],
            "BLOCKED_NO_EXECUTOR",
        )

    def test_unknown_mode_is_blocked(self):
        result = self.adapter.execute({"mode": "auto"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["error"], "UNSUPPORTED_MODE")


if __name__ == "__main__":
    unittest.main()
