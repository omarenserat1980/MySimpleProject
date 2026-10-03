import unittest
from brain_v12.brain.success_bot import SuccessBot
from brain_v12.brain.brain_ai import BrainAI

class SuccessBotTests(unittest.TestCase):
    def test_goal_requires_verification_for_success(self):
        bot = SuccessBot(max_cycles=2)
        state = bot.create_goal("build a working Brain feature", ["tests_pass", "runtime_evidence"])
        bot.update(state, progress=70, evidence={"tests_pass": True})
        self.assertNotEqual(state.status, "VERIFIED_COMPLETED")
        bot.verify(state, {"ok": True, "tests_pass": True, "runtime_evidence": True})
        self.assertEqual(state.status, "VERIFIED_COMPLETED")
        self.assertEqual(state.progress, 100)

    def test_failed_verification_does_not_report_success(self):
        bot = SuccessBot(max_cycles=2)
        state = bot.create_goal("ship feature")
        bot.verify(state, {"ok": False, "error": "runtime_failed"})
        self.assertNotEqual(state.status, "VERIFIED_COMPLETED")
        self.assertLess(state.progress, 100)

    def test_goal_is_registered_and_can_be_retrieved(self):
        bot = SuccessBot()
        state = bot.create_goal("registered")
        self.assertEqual(bot.get_goal(state.goal_id), state)
        self.assertEqual(bot.snapshot_by_id(state.goal_id)["goal"], "registered")

    def test_snapshot_is_serializable(self):
        bot = SuccessBot()
        state = bot.create_goal("test")
        self.assertEqual(bot.snapshot(state)["goal"], "test")

    def test_brain_ai_exposes_success_bot_tools(self):
        class Provider:
            def respond(self, *args, **kwargs):
                return {"ok": True, "reply": "ok"}

        ai = BrainAI(Provider(), github=None)
        for name in ("success.create", "success.start", "success.update", "success.verify", "success.status"):
            self.assertIn(name, ai.tools)
        created = ai.execute_tool("success.create", {"goal": "ship", "success_criteria": ["tests"]})
        self.assertTrue(created["ok"])
        self.assertEqual(created["status"], "GOAL_CREATED")
        goal_id = created["goal"]["goal_id"]
        verified = ai.execute_tool("success.verify", {"goal_id": goal_id, "verification": {"ok": True, "tests": True}})
        self.assertTrue(verified["ok"])
        self.assertEqual(verified["status"], "VERIFIED_COMPLETED")
        self.assertEqual(verified["goal"]["progress"], 100)

if __name__ == "__main__":
    unittest.main()
