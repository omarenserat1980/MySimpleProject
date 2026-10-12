import unittest
from brain_v12.ai_fabric import AIFabric, FabricPolicy

class AIFabricTests(unittest.TestCase):
    def test_free_first_and_verified_execution(self):
        f=AIFabric(FabricPolicy(max_attempts=3))
        f.register("paid","model",lambda p: {"ok":True,"verified":True,"result":"paid"},free=False,priority=1)
        f.register("free","model",lambda p: {"ok":True,"verified":True,"result":"free"},free=True,priority=50)
        r=f.execute("chat",{})
        self.assertTrue(r["ok"]); self.assertEqual(r["capability"],"free")
        self.assertTrue(r["evidence"]["evidence_id"].startswith("fabric-"))

    def test_unverified_is_not_success(self):
        f=AIFabric(FabricPolicy(max_attempts=1))
        f.register("bad","model",lambda p: {"ok":True,"verified":False})
        r=f.execute("chat",{})
        self.assertFalse(r["ok"]); self.assertEqual(r["status"],"ALL_CAPABILITIES_FAILED")

    def test_fallback_after_failure(self):
        f=AIFabric(FabricPolicy(max_attempts=2))
        f.register("first","model",lambda p: {"ok":False},priority=1)
        f.register("second","model",lambda p: {"ok":True,"verified":True,"result":"fallback"},priority=2)
        r=f.execute("chat",{})
        self.assertTrue(r["ok"]); self.assertEqual(r["capability"],"second")

    def test_consensus_requires_agreement(self):
        f=AIFabric(FabricPolicy(max_attempts=3))
        f.register("a","model",lambda p: {"ok":True,"verified":True,"result":"same"},priority=1)
        f.register("b","model",lambda p: {"ok":True,"verified":True,"result":"same"},priority=2)
        r=f.consensus("reasoning",{},2)
        self.assertTrue(r["ok"]); self.assertEqual(r["status"],"CONSENSUS_VERIFIED")

if __name__=="__main__": unittest.main()
