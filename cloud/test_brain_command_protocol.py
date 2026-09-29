import unittest
from cloud.brain_command_protocol import issue_command

class BrainCommandProtocolTests(unittest.TestCase):
    def test_brain_can_issue_structured_request(self):
        cmd = issue_command(
            "repair",
            "Inspect the latest cinematic self-healing failure and repair only the known failure class.",
            "Brain identified a production blocker.",
            ["test result", "repair diff", "post-repair verification"],
            "high",
        )
        self.assertEqual(cmd["source"], "Brain Cloud")
        self.assertEqual(cmd["status"], "REQUESTED")
        self.assertTrue(cmd["authorization_required"])
        self.assertFalse(cmd["arbitrary_code"])

    def test_arbitrary_execution_is_rejected(self):
        from cloud.brain_command_protocol import BrainCommand
        with self.assertRaises(ValueError):
            BrainCommand(
                "x", "repair", "anything", "reason", ("evidence",),
                arbitrary_code=True
            ).validate()

if __name__ == "__main__":
    unittest.main()
