import unittest

from brain_v12.brain.income_strategy import IncomeStrategy


class FakeEngine:
    def snapshot(self):
        return {"verified_revenue_jod": 0.0}


class IncomeStrategyTests(unittest.TestCase):
    def test_first_target_is_ten_jod(self):
        mission = IncomeStrategy(FakeEngine()).mission()
        self.assertEqual(mission["mission"], "FIRST_VERIFIED_10_JOD")
        self.assertEqual(mission["target_jod"], 10.0)
        self.assertEqual(mission["gap_jod"], 10.0)
        self.assertGreaterEqual(len(mission["priority"]), 5)
        self.assertIn("verifier", mission["prompts"])

    def test_search_plan_contains_sources_and_evidence(self):
        plan = IncomeStrategy(FakeEngine()).search_plan()
        self.assertTrue(plan["ok"])
        self.assertGreaterEqual(len(plan["queries"]), 5)
        self.assertIn("url", plan["evidence_required"])
        self.assertIn("retrieved_at", plan["evidence_required"])


if __name__ == "__main__":
    unittest.main()
