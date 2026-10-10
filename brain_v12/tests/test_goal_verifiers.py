import unittest

from brain_v12.brain.goal_verifiers import VERIFIER_ID, verify_cognitive_goal


class GoalVerifierTests(unittest.TestCase):
    def test_read_only_system_status_goal_requires_structured_status_evidence(self):
        result = verify_cognitive_goal(
            "check system status",
            {"tool": "state.read"},
            {"ok": True, "tool": "state.read", "data": {"status": "READY"}},
        )

        self.assertTrue(result["verified"])
        self.assertEqual(result["verifier"], VERIFIER_ID)
        self.assertIn("READY", result["evidence"])

    def test_status_goal_does_not_verify_when_status_field_is_missing(self):
        result = verify_cognitive_goal(
            "check system status",
            {"tool": "state.read"},
            {"ok": True, "tool": "state.read", "data": {"cognitive_stage": "READY"}},
        )

        self.assertFalse(result["verified"])
        self.assertEqual(result["evidence"], "")

    def test_read_only_memory_listing_requires_list_output(self):
        result = verify_cognitive_goal(
            "list brain memories",
            {"tool": "memory.read"},
            {"ok": True, "tool": "memory.read", "data": [{"key": "project.source"}]},
        )

        self.assertTrue(result["verified"])
        self.assertIn("1 record", result["evidence"])

    def test_successful_tool_does_not_verify_a_mutating_goal(self):
        result = verify_cognitive_goal(
            "fix system status",
            {"tool": "state.read"},
            {"ok": True, "tool": "state.read", "data": {"status": "READY"}},
        )

        self.assertFalse(result["verified"])
        self.assertEqual(result["reason"], "MUTATING_OR_BROAD_GOAL_NOT_COVERED")

    def test_unrelated_tool_result_does_not_verify_status_goal(self):
        result = verify_cognitive_goal(
            "check system status",
            {"tool": "tasks.create"},
            {"ok": True, "tool": "tasks.create", "data": {"id": "task-1"}},
        )

        self.assertFalse(result["verified"])
        self.assertEqual(result["reason"], "NO_MATCHING_READ_ONLY_VERIFIER")

    def test_failed_tool_result_never_verifies_goal(self):
        result = verify_cognitive_goal(
            "check system status",
            {"tool": "state.read"},
            {"ok": False, "tool": "state.read", "data": {"status": "READY"}},
        )

        self.assertFalse(result["verified"])
        self.assertEqual(result["reason"], "TOOL_RESULT_NOT_OK")


if __name__ == "__main__":
    unittest.main()
