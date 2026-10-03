import unittest

from brain_v12.app import brain_ai


class BrainAISupervisorWiringTests(unittest.TestCase):
    def test_supervisor_solve_tool_is_registered(self):
        self.assertIn("supervisor.solve", brain_ai.tools)
        tool = brain_ai.tools["supervisor.solve"]
        self.assertEqual(tool.risk, "medium")
        self.assertIn("verification", tool.description.lower())

    def test_supervisor_solve_rejects_empty_goal(self):
        result = brain_ai.execute_tool("supervisor.solve", {}, approved=False)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "EMPTY_GOAL")


if __name__ == "__main__":
    unittest.main()
