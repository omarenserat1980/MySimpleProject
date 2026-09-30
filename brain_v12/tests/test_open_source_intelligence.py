import json
import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.open_source_intelligence import snapshot, write_snapshot
from brain_v12.brain.learning_router import rank, record_observation
from brain_v12.brain.agent_cycle import run

class IntelligenceTests(unittest.TestCase):
    def test_snapshot_contains_reusable_patterns(self):
        data=snapshot()
        self.assertGreaterEqual(len(data["patterns"]), 6)
        self.assertFalse(data["policy"]["copy_third_party_code"])

    def test_learning_changes_order_only_from_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            path=str(Path(d)/"obs.jsonl")
            for _ in range(8):
                record_observation("b","task",True,path=path)
            record_observation("a","task",False,path=path)
            from brain_v12.brain.learning_router import load_observations
            ranked=rank([{"id":"a"},{"id":"b"}],"task",load_observations(path))
            self.assertEqual(ranked[0]["id"],"b")

    def test_agent_cycle_retries_and_verifies(self):
        seen=[]
        def action(task, attempt):
            seen.append(attempt)
            return {"attempt":attempt}
        result=run("x",action,lambda out: out["attempt"] >= 2,max_attempts=3)
        self.assertTrue(result.success)
        self.assertEqual(result.attempts,2)
        self.assertEqual(seen,[1,2])

if __name__=="__main__":
    unittest.main()
