import tempfile
import unittest

from brain_v12.brain.memory import MemoryStore
from brain_v12.brain.core import BrainCore

class BrainCoreTests(unittest.TestCase):
    def make_brain(self):
        fd=tempfile.NamedTemporaryFile(suffix=".db",delete=False)
        fd.close()
        store=MemoryStore(fd.name)
        store.init()
        return store, BrainCore(store)

    def test_cycle_creates_decision(self):
        store, brain=self.make_brain()
        gid=store.add_goal("اختبار العقل",0.8)
        result=brain.think()
        self.assertEqual(result["status"],"DECIDING")
        self.assertEqual(result["goal_id"],gid)
        self.assertIsNotNone(result["selected"])

    def test_observe_matching_prediction_completes_goal(self):
        store, brain=self.make_brain()
        gid=store.add_goal("هدف ناجح",0.8)
        decision=brain.think()
        result=brain.observe(decision["prediction"])
        self.assertTrue(result["ok"])
        self.assertEqual(result["state"]["prediction_error"],0.0)
        self.assertEqual(store.active_goal(),None)

if __name__=="__main__":
    unittest.main()
