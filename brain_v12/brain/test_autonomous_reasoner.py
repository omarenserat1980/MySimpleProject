import unittest
from brain_v12.brain.autonomous_reasoner import AutonomousReasoner

class AutonomousReasonerTests(unittest.TestCase):
    def test_no_failure_requires_verification(self):
        d=AutonomousReasoner().next({"verified":False,"failures":[],"attempts":0,"max_attempts":3})
        self.assertEqual(d.action,"verify")
        self.assertIn("self_test",d.required_tests)
    def test_media_failure_selects_media_tests(self):
        d=AutonomousReasoner().next({"failures":[{"id":"f1","class":"MEDIA_PIPELINE"}],"attempts":0,"max_attempts":3})
        self.assertEqual(d.action,"repair")
        self.assertIn("cinematic_qc",d.required_tests)
    def test_budget_blocks(self):
        d=AutonomousReasoner().next({"failures":[{"id":"f1","class":"UNKNOWN"}],"attempts":3,"max_attempts":3})
        self.assertEqual(d.action,"block")
    def test_verified_delivers(self):
        d=AutonomousReasoner().next({"verified":True,"failures":[],"attempts":1,"max_attempts":3})
        self.assertEqual(d.action,"deliver")

if __name__=="__main__": unittest.main()
