import unittest
from brain_v12.ai_fabric import AIFabric
from brain_v12.ai_fabric.self_healing import repair_execute
from brain_v12.ai_fabric.benchmark import benchmark

class AIFabricV3LoopTests(unittest.TestCase):
    def test_benchmark_updates_learning(self):
        f = AIFabric()
        f.register("good", "agent", lambda p: {"ok": True, "verified": True}, priority=10, free=True)
        rows = benchmark(f, "task", {}, kind="agent")
        self.assertTrue(rows[0].verified)
        self.assertEqual(f.intelligence.stats["good"].verified, 1)

    def test_self_healing_uses_verified_result(self):
        f = AIFabric()
        f.register("good", "agent", lambda p: {"ok": True, "verified": True}, priority=10, free=True)
        r = repair_execute(f, "task", {}, "agent")
        self.assertTrue(r["ok"])
        self.assertEqual(r["status"], "SELF_HEALING_VERIFIED")
        self.assertEqual(r["selected"], "good")

    def test_learning_changes_ranking(self):
        f = AIFabric()
        f.register("a", "agent", lambda p: {"ok": True, "verified": True}, priority=50, free=True)
        f.register("b", "agent", lambda p: {"ok": False}, priority=10, free=True)
        f.intelligence.observe("b", ok=False, verified=False)
        f.intelligence.observe("b", ok=False, verified=False)
        self.assertEqual(f._candidates(f.agents, "task")[0].name, "a")

if __name__ == "__main__":
    unittest.main()
