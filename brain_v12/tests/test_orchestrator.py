import tempfile
import unittest
from brain_v12.brain.memory import MemoryStore
from brain_v12.brain.core import BrainCore
from brain_v12.brain.builder import SoftwareBuilder
from brain_v12.brain.orchestrator import CognitiveOrchestrator

class OrchestratorTests(unittest.TestCase):
    def test_run_builds_plan_from_active_goal(self):
        path=tempfile.NamedTemporaryFile(suffix=".db",delete=False).name
        store=MemoryStore(path); store.init()
        brain=BrainCore(store); store.add_goal("بناء دورة معرفية",0.9)
        result=CognitiveOrchestrator(store,brain,SoftwareBuilder()).run()
        self.assertEqual(result["status"],"PLANNED")
        self.assertTrue(result["plan"]["steps"])
        self.assertEqual(store.state()["status"],"PLANNED")

if __name__=="__main__":
    unittest.main()
