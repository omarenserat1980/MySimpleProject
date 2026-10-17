import json
import tempfile
import unittest

from brain_v12.brain.cognitive_loop import CognitiveLoop
from brain_v12.brain.logic_unit import LogicUnit
from brain_v12.brain.memory import MemoryStore


class LogicUnitTests(unittest.TestCase):
    def make_store(self):
        handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        handle.close()
        store = MemoryStore(handle.name)
        store.init()
        return store

    def test_logic_unit_is_persisted_and_context_tracks_memory_and_path(self):
        store = self.make_store()
        store.save_memory("lesson.worker", "A verified worker test passed.")
        unit = LogicUnit(store)
        memories = store.recall_memories("worker", limit=12)
        path = {
            "key": "reasoning_path.quranic.test",
            "title": "Bounded reasoning path",
        }

        context = unit.activate(
            goal="verify worker",
            memories=memories,
            reasoning_path=path,
            run_id="run-test",
        )
        traced = unit.trace(context)
        decision_memories = unit.decision_memories(memories, context)

        saved = {item["key"]: item["value"] for item in store.memories()}
        definition = json.loads(saved[unit.MEMORY_KEY])
        self.assertEqual(definition["unit_id"], "brain.logic-unit")
        self.assertIn("lesson.worker", traced["memory_keys"])
        self.assertEqual(traced["reasoning_path_key"], path["key"])
        self.assertEqual(decision_memories[-1]["key"], unit.MEMORY_KEY)
        self.assertIn("permissions_win", traced["rule_ids"])

        unit.record_run(context, {"outcome": "VERIFIED_SUCCESS", "verified": True})
        latest = json.loads({item["key"]: item["value"] for item in store.memories()}["brain.logic_unit.last_run"])
        self.assertEqual(latest["run_id"], "run-test")
        self.assertTrue(latest["verified"])

    def test_cognitive_loop_exposes_logic_unit_and_persists_run_trace(self):
        store = self.make_store()
        store.save_memory("lesson.general", "A previous task was verified.")
        loop = CognitiveLoop(store)

        result = loop.run("حلل هدف بسيط")

        self.assertEqual(result["logic_unit"]["unit_id"], "brain.logic-unit")
        self.assertEqual(result["logic_unit"]["run_id"], result["run_id"])
        self.assertIn("logic_unit", result["decision"])
        self.assertIn("logic_unit", result["verification"])
        records = {item["key"]: item["value"] for item in store.memories()}
        self.assertIn("brain.logic_unit.core.v1", records)
        self.assertIn("brain.logic_unit.last_run", records)
        self.assertIn(f"cognitive.run.{result['run_id']}", records)


if __name__ == "__main__":
    unittest.main()
