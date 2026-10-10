import json
import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.memory import MemoryStore
from brain_v12.brain.cognitive_loop import CognitiveLoop
from brain_v12.brain.quranic_reasoning_paths import (
    PATHWAYS,
    register_quranic_reasoning_paths,
    select_reasoning_path,
)


class QuranicReasoningPathTests(unittest.TestCase):
    def test_paths_are_seeded_with_references_and_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(str(Path(directory) / "brain.db"))
            store.init()
            result = register_quranic_reasoning_paths(store)
            records = [m for m in store.memories() if m["key"].startswith("reasoning_path.quranic.")]

            self.assertEqual(result["total"], len(PATHWAYS))
            self.assertEqual(len(records), len(PATHWAYS))
            for record in records:
                value = json.loads(record["value"])
                self.assertTrue(value["source_references"])
                self.assertTrue(value["limits"])
                self.assertEqual(value["interpretation_type"], "bounded_engineering_inference")

    def test_registration_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(str(Path(directory) / "brain.db"))
            store.init()
            self.assertEqual(register_quranic_reasoning_paths(store)["registered"], len(PATHWAYS))
            self.assertEqual(register_quranic_reasoning_paths(store)["registered"], 0)

    def test_relevant_goal_selects_path_and_unrelated_goal_does_not(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(str(Path(directory) / "brain.db"))
            store.init()
            register_quranic_reasoning_paths(store)
            relevant = store.recall_memories("التحقق من مصدر الخبر والدليل", limit=12)
            selected = select_reasoning_path("التحقق من مصدر الخبر والدليل", relevant)
            unrelated = select_reasoning_path("كم درجة الحرارة في عمان اليوم", store.recall_memories("كم درجة الحرارة في عمان اليوم", limit=12))

            self.assertIsNotNone(selected)
            self.assertEqual(selected["id"], "verify_before_action")
            self.assertIsNone(unrelated)

    def test_cognitive_loop_uses_selected_path_as_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(str(Path(directory) / "brain.db"))
            store.init()
            register_quranic_reasoning_paths(store)

            result = CognitiveLoop(store).run("التحقق من مصدر الخبر والدليل")

            self.assertEqual(result["reasoning_path"]["key"], "reasoning_path.quranic.verify_before_action")
            self.assertEqual(result["plan_steps"], result["reasoning_path"]["stages"])
            self.assertTrue(result["decision"]["selected"]["memory_context_keys"])


if __name__ == "__main__":
    unittest.main()
