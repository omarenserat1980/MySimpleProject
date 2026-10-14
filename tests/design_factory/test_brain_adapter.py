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

    def test_non_dry_run_without_executor_mode_fails_closed(self):
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

    def test_explicit_simulation_runs_exactly_one_step_and_marks_evidence(self):
        planned = self.adapter.execute({"task": "Bitcoin ASIC RTL and OpenROAD physical design"})
        result = self.adapter.execute({
            "mode": "step",
            "execution_ledger": planned["execution_ledger"],
            "authorize": True,
            "dry_run": False,
            "executor_mode": "simulation",
        })
        ledger = result["execution_ledger"]
        first = ledger["steps"][0]
        self.assertTrue(result["ok"])
        self.assertEqual(first["status"], "SIMULATED")
        self.assertTrue(result["execution_started"])
        self.assertEqual(ledger["next_step_index"], 1)
        self.assertEqual(sum(step["started"] for step in ledger["steps"]), 1)
        self.assertEqual(first["evidence"]["kind"], "SIMULATION")
        self.assertFalse(first["evidence"]["physical_execution"])
        self.assertFalse(first["evidence"]["external_side_effects"])
        self.assertIn("not_mining_evidence", first["evidence"]["limitations"])
        self.assertNotEqual(first["status"], "VERIFIED")

    def test_simulation_requires_explicit_authorization(self):
        planned = self.adapter.execute({"task": "Bitcoin ASIC RTL and OpenROAD physical design"})
        result = self.adapter.execute({
            "mode": "step",
            "execution_ledger": planned["execution_ledger"],
            "authorize": False,
            "dry_run": False,
            "executor_mode": "simulation",
        })
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(
            result["execution_ledger"]["steps"][0]["evidence"]["reason"],
            "EXPLICIT_AUTHORIZATION_REQUIRED",
        )

    def test_unknown_executor_mode_is_blocked(self):
        planned = self.adapter.execute({"task": "Bitcoin ASIC RTL and OpenROAD physical design"})
        result = self.adapter.execute({
            "mode": "step",
            "execution_ledger": planned["execution_ledger"],
            "executor_mode": "remote",
        })
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["error"], "UNSUPPORTED_EXECUTOR_MODE")

    def test_unknown_mode_is_blocked(self):
        result = self.adapter.execute({"mode": "auto"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["error"], "UNSUPPORTED_MODE")


if __name__ == "__main__":
    unittest.main()
