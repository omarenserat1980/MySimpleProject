import unittest
from brain_v12.design_factory.task_router import route_task

class RouterTests(unittest.TestCase):
    def test_asic_physical_design_routes_to_rtl_and_physical(self):
        result = route_task("Run Bitcoin ASIC RTL and OpenROAD physical design verification")
        self.assertIn("digital_logic", result["domains"])
        self.assertIn("physical_design", result["domains"])
        self.assertIn("06", result["prompt_ids"])
        self.assertIn("07", result["prompt_ids"])
        self.assertIn("00", result["prompt_ids"])
        self.assertIn("10", result["prompt_ids"])
        self.assertTrue(result["review_required"])

    def test_unknown_domain_routes_to_new_domain_prompt(self):
        result = route_task("design an unlisted domain")
        self.assertIn("new_domain", result["domains"])
        self.assertIn("15", result["prompt_ids"])

    def test_substrings_inside_other_words_do_not_trigger_domains(self):
        result = route_task("design a new unlisted specialty")
        self.assertEqual(result["domains"], ["new_domain"])
        self.assertNotIn("requirements", result["domains"])
        self.assertNotIn("infrastructure", result["domains"])

    def test_empty_task_is_rejected(self):
        with self.assertRaises(ValueError):
            route_task("  ")

if __name__ == "__main__":
    unittest.main()
