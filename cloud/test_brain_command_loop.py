import unittest
from cloud.brain_command_loop import next_from_result

class BrainCommandLoopTests(unittest.TestCase):
    def test_verified_requests_independent_verification(self):
        out=next_from_result({"status":"VERIFIED","evidence":["proof"]})
        self.assertEqual(out["intent"],"verify")

    def test_failed_requests_bounded_inspection(self):
        out=next_from_result({"status":"FAILED","evidence":["failure"]})
        self.assertEqual(out["intent"],"inspect")

    def test_blocked_requests_bounded_inspection(self):
        out=next_from_result({"status":"BLOCKED","evidence":["block"]})
        self.assertEqual(out["intent"],"inspect")

    def test_pending_requests_report(self):
        out=next_from_result({"status":"EXECUTED","evidence":["run"]})
        self.assertEqual(out["intent"],"report")

if __name__=="__main__":
    unittest.main()
