import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.memory import MemoryStore


class MemoryRecallTests(unittest.TestCase):
    def test_recall_prefers_relevant_older_memory_over_recent_unrelated_records(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(str(Path(directory) / "brain.db"))
            store.init()
            store.save_memory("project.github.repository", "فحص مستودع GitHub والالتزامات والفروع")
            for index in range(20):
                store.save_memory(f"recent.unrelated.{index}", f"الطقس والرياضة رقم {index}")

            recalled = store.recall_memories("افحص مستودع GitHub والفروع", limit=5)

            self.assertEqual(recalled[0]["key"], "project.github.repository")
            self.assertLessEqual(len(recalled), 5)

    def test_recall_supports_arabic_normalization(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(str(Path(directory) / "brain.db"))
            store.init()
            store.save_memory("source.verification", "التحقق من مصدر المعلومة قبل القرار")

            recalled = store.recall_memories("التحقّق من مصدر المعلومة", limit=3)

            self.assertTrue(recalled)
            self.assertEqual(recalled[0]["key"], "source.verification")

    def test_recall_falls_back_to_recent_memories_when_nothing_matches(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(str(Path(directory) / "brain.db"))
            store.init()
            store.save_memory("memory.one", "معلومة أولى")
            store.save_memory("memory.two", "معلومة ثانية")

            recalled = store.recall_memories("مجرة بعيدة", limit=1)

            self.assertEqual([item["key"] for item in recalled], ["memory.two"])


if __name__ == "__main__":
    unittest.main()
