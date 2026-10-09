import json
import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.cognitive_loop import CognitiveLoop
from brain_v12.brain.memory import MemoryStore


class CognitiveLearningMemoryTests(unittest.TestCase):
    def test_each_run_keeps_a_separate_structured_learning_record(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(str(Path(directory) / "brain.db"))
            store.init()
            loop = CognitiveLoop(store)

            first = loop.run("observe status")
            second = loop.run("observe status")

            memories = {item["key"]: item["value"] for item in store.memories()}
            first_key = f"cognitive.run.{first['run_id']}"
            second_key = f"cognitive.run.{second['run_id']}"

            self.assertIn(first_key, memories)
            self.assertIn(second_key, memories)
            self.assertNotEqual(first_key, second_key)

            first_lesson = json.loads(memories[first_key])
            second_lesson = json.loads(memories[second_key])
            self.assertEqual(first_lesson["run_id"], first["run_id"])
            self.assertEqual(second_lesson["run_id"], second["run_id"])
            self.assertIn(first_lesson["outcome"], {
                "VERIFIED_SUCCESS", "WAITING_PERMISSION", "FAILED_OR_UNVERIFIED"
            })
            self.assertIn("verified", second_lesson)
            self.assertGreaterEqual(second["prior_lesson_count"], 1)


if __name__ == "__main__":
    unittest.main()
