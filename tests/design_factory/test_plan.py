import unittest
from brain_v12.design_factory.plan import prepare_design_plan

class DesignPlanTests(unittest.TestCase):
    def test_asic_physical_task_has_ordered_domains_gates_and_prompt_files(self):
        plan = prepare_design_plan("Bitcoin ASIC RTL and OpenROAD physical design verification")
        self.assertEqual(plan["status"], "PLANNED")
        self.assertFalse(plan["execution_started"])
        self.assertIn("digital_logic", plan["domains"])
        self.assertIn("physical_design", plan["domains"])
        self.assertIn("G7_PHYSICAL", plan["required_gates"])
        self.assertIn("G5_EVIDENCE", plan["required_gates"])
        self.assertTrue(plan["review_required"])
        selected = {p["id"]: p for p in plan["selected_prompts"]}
        self.assertIn("06", selected)
        self.assertIn("07", selected)
        self.assertTrue(selected["06"]["path"].endswith("06_digital_logic_hardware.md"))
        self.assertTrue(selected["07"]["path"].endswith("07_physical_design.md"))

    def test_unknown_domain_is_planned_not_executed(self):
        plan = prepare_design_plan("design a new unlisted specialty")
        self.assertEqual(plan["domains"], ["new_domain"])
        self.assertEqual(plan["status"], "PLANNED")
        self.assertFalse(plan["execution_started"])
        self.assertTrue(any(p["id"] == "15" for p in plan["selected_prompts"]))

    def test_blank_task_rejected(self):
        with self.assertRaises(ValueError):
            prepare_design_plan("  ")

if __name__ == "__main__":
    unittest.main()
