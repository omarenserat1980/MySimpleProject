import unittest
from brain_v12.brain.success_bot import SuccessBot

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

    def test_snapshot_is_serializable(self):
        bot = SuccessBot()
        state = bot.create_goal("test")
        self.assertEqual(bot.snapshot(state)["goal"], "test")

if __name__ == "__main__":
    unittest.main()
