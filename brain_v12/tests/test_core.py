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

    def test_cognitive_loop_passes_recent_memories_into_decision(self):
        from brain_v12.brain.cognitive_loop import CognitiveLoop

        fd = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        fd.close()
        store = MemoryStore(fd.name)
        store.init()
        store.save_memory("old", "older context")
        store.save_memory("recent", "recent context")
        loop = CognitiveLoop(store)

        seen = {}
        original_generate = loop.decisions.generate
        original_choose = loop.decisions.choose

        def generate(goal, memories=None):
            seen["generate"] = memories
            return original_generate(goal, memories=memories)

        def choose(goal, options, permissions=None, memories=None):
            seen["choose"] = memories
            return original_choose(goal, options, permissions, memories=memories)

        loop.decisions.generate = generate
        loop.decisions.choose = choose
        result = loop.run("اقرأ الذاكرة")

        self.assertEqual([item["key"] for item in seen["generate"]], ["recent", "old"])
        self.assertEqual(seen["generate"], seen["choose"])
        self.assertEqual(result["memory_count"], 2)

if __name__=="__main__":
    unittest.main()
