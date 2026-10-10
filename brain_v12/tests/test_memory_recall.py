import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.memory import MemoryStore


class MemoryRecallTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = MemoryStore(str(Path(self.temp_dir.name) / "brain.db"))
        self.store.init()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_relevant_memory_beats_newer_unrelated_memory(self):
        self.store.save_memory("ذاكرة العقل الأساسية", "استرجاع الذكريات ذات الصلة بالهدف")
        self.store.save_memory("حالة الطقس", "معلومة أحدث لكنها لا تتعلق بالذاكرة")
        recalled = self.store.recall_memories("ذاكرة العقل", limit=2)
        self.assertEqual(recalled[0]["key"], "ذاكرة العقل الأساسية")

    def test_unmatched_query_falls_back_to_recent_memories(self):
        self.store.save_memory("قديم", "سجل قديم")
        self.store.save_memory("أحدث", "سجل أحدث")
        recalled = self.store.recall_memories("موضوع لا يوجد في الذاكرة", limit=1)
        self.assertEqual(len(recalled), 1)
        self.assertEqual(recalled[0]["key"], "أحدث")

    def test_limit_is_bounded_and_empty_store_is_safe(self):
        self.assertEqual(self.store.recall_memories("أي شيء"), [])
        self.store.save_memory("ذاكرة واحد", "قيمة")
        self.store.save_memory("ذاكرة اثنان", "قيمة")
        self.assertEqual(len(self.store.recall_memories("", limit=1)), 1)


if __name__ == "__main__":
    unittest.main()
