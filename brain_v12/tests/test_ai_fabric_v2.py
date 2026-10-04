import unittest
from brain_v12.ai_fabric import AIFabric

class AIFabricV2Tests(unittest.TestCase):
    def test_benchmark(self):
        from brain_v12.ai_fabric.benchmark import benchmark
        f=AIFabric()
        f.register("m","model",lambda p: {"ok":True,"verified":True,"result":"x"})
        rows=benchmark(f,"x",{})
        self.assertEqual(len(rows),1)
        self.assertTrue(rows[0].verified)

    def test_self_healing_is_bounded(self):
        from brain_v12.ai_fabric.self_healing import repair_execute
        f=AIFabric()
        f.register("bad","model",lambda p: {"ok":False})
        r=repair_execute(f,"x",{})
        self.assertFalse(r["ok"])
        self.assertEqual(len(r["attempts"]),3)
