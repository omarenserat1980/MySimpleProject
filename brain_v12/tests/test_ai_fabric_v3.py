import unittest
from brain_v12.ai_fabric.fabric import Capability
from brain_v12.ai_fabric.intelligence import FabricIntelligence

class AIFabricV3Tests(unittest.TestCase):
    def test_learning_prefers_verified_capability(self):
        i=FabricIntelligence()
        i.observe("bad",ok=False,verified=False,latency_ms=1)
        i.observe("good",ok=True,verified=True,latency_ms=1)
        caps=[
            Capability("bad","agent",lambda p: {},priority=1,free=True),
            Capability("good","agent",lambda p: {},priority=50,free=True),
        ]
        self.assertEqual(i.rank(caps,"task")[0].name,"good")

    def test_snapshot_is_evidence_state(self):
        i=FabricIntelligence()
        i.observe("x",ok=True,verified=True,latency_ms=10)
        s=i.snapshot()
        self.assertEqual(s["capabilities"]["x"]["verified"],1)
        self.assertEqual(s["capabilities"]["x"]["runs"],1)

if __name__ == "__main__":
    unittest.main()
