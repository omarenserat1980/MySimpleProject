import unittest
from cloud.brain_command_stream import create_next_command

class BrainCommandStreamTests(unittest.TestCase):
    def test_first_command_is_concrete_and_evidence_bound(self):
        command = create_next_command()
        self.assertEqual(command["source"], "Brain Cloud")
        self.assertEqual(command["status"], "REQUESTED")
        self.assertEqual(command["intent"], "inspect")
        self.assertGreaterEqual(len(command["evidence_required"]), 3)

if __name__ == "__main__":
    unittest.main()
