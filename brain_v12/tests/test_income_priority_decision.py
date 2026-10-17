import unittest

from brain_v12.brain.decision_engine import DecisionEngine


class NeverCallBitcoinCompass:
    def assess(self, task):
        raise AssertionError("Bitcoin-only compass must not veto non-Bitcoin income goals")


class IncomePriorityDecisionTests(unittest.TestCase):
    def test_income_goal_generates_a_direct_opportunity_search(self):
        engine = DecisionEngine(north_star=NeverCallBitcoinCompass())
        options = engine.generate("find income and earn money from freelance work")
        self.assertEqual(options[0]["id"], "income_opportunities")
        self.assertEqual(options[0]["tool_id"], "income.search")

    def test_income_goal_is_not_blocked_by_bitcoin_only_mission_gate(self):
        engine = DecisionEngine(north_star=NeverCallBitcoinCompass())
        options = engine.generate("ابحث عن فرص دخل مدفوعة")
        result = engine.choose("ابحث عن فرص دخل مدفوعة", options)
        self.assertEqual(result["status"], "DECIDED")
        self.assertEqual(result["selected"]["id"], "income_opportunities")
        self.assertEqual(result["north_star"]["status"], "NOT_APPLICABLE")

    def test_income_scoring_prefers_opportunity_over_generic_planning(self):
        engine = DecisionEngine(north_star=NeverCallBitcoinCompass())
        options = [
            {"id": "plan", "action": "make a plan", "confidence": 0.95, "risk": "low", "requirements": []},
            {"id": "income_opportunities", "action": "find income opportunities", "confidence": 0.80, "risk": "low", "requirements": []},
        ]
        result = engine.choose("find income", options)
        self.assertEqual(result["selected"]["id"], "income_opportunities")

    def test_bitcoin_goals_still_use_the_bitcoin_compass(self):
        class Compass:
            def __init__(self):
                self.called = False
            def assess(self, task):
                self.called = True
                class Assessment:
                    status = "ON_MISSION"
                    next_action = "verify mining evidence"
                    def as_dict(self):
                        return {"status": self.status}
                return Assessment()
        compass = Compass()
        engine = DecisionEngine(north_star=compass)
        result = engine.choose("verify Bitcoin mining profit", engine.generate("verify Bitcoin mining profit"))
        self.assertTrue(compass.called)
        self.assertEqual(result["status"], "DECIDED")


if __name__ == "__main__":
    unittest.main()
