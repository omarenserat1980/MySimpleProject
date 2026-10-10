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


    def test_goal_directed_recall_does_not_fallback_for_empty_normalized_query(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(str(Path(directory) / "brain.db"))
            store.init()
            store.save_memory("recent.unrelated", "معلومة غير مرتبطة")
            self.assertEqual(store.recall_memories("the and to", limit=5, fallback_recent=False), [])

    def test_goal_directed_recall_can_avoid_unrelated_recent_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(str(Path(directory) / "brain.db"))
            store.init()
            store.save_memory("recent.unrelated", "طقس ورياضة")
            recalled = store.recall_memories("مجرة بعيدة", limit=5, fallback_recent=False)
            self.assertEqual(recalled, [])


    def test_memory_metadata_round_trips_source_confidence_status_and_tags(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(str(Path(directory) / "brain.db"))
            store.init()
            store.save_memory("project.decision", "قرار مرتبط بمصدر موثق")
            metadata = store.set_memory_metadata(
                "project.decision",
                source="github:commit:abc123",
                confidence=0.93,
                status="ACTIVE",
                tags=["decision", "source"],
            )
            recalled = store.memories()[0]

            self.assertEqual(metadata["source"], "github:commit:abc123")
            self.assertEqual(metadata["confidence"], 0.93)
            self.assertEqual(recalled["source"], "github:commit:abc123")
            self.assertEqual(recalled["confidence"], 0.93)
            self.assertEqual(recalled["status"], "ACTIVE")
            self.assertEqual(recalled["tags"], ["decision", "source"])

    def test_expired_memory_is_excluded_even_when_query_matches(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(str(Path(directory) / "brain.db"))
            store.init()
            store.save_memory("project.expired", "deployment verification evidence")
            store.set_memory_metadata("project.expired", source="test", expires_at="2000-01-01T00:00:00Z")

            recalled = store.recall_memories("deployment verification evidence", fallback_recent=False)

            self.assertEqual(recalled, [])

    def test_conflicted_retracted_and_archived_memories_are_not_recalled(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(str(Path(directory) / "brain.db"))
            store.init()
            for key, status in [
                ("project.conflicted", "CONFLICTED"),
                ("project.retracted", "RETRACTED"),
                ("project.archived", "ARCHIVED"),
            ]:
                store.save_memory(key, "deployment verified evidence")
                store.set_memory_metadata(key, status=status, source="test")

            recalled = store.recall_memories("deployment verified evidence", fallback_recent=False)

            self.assertEqual(recalled, [])

    def test_malformed_expiry_fails_closed_for_goal_recall(self):
        self.assertFalse(MemoryStore._memory_is_recallable({
            "key": "project.bad_expiry",
            "value": "matching evidence",
            "status": "ACTIVE",
            "expires_at": "not-a-date",
        }))

    def test_legacy_memory_without_metadata_remains_recallable(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(str(Path(directory) / "brain.db"))
            store.init()
            store.save_memory("project.legacy", "historical repository evidence")
            with store.connect() as con:
                con.execute("DELETE FROM memory_metadata WHERE memory_key=?", ("project.legacy",))
                con.commit()

            memory = store.memories()[0]
            recalled = store.recall_memories("historical repository evidence", fallback_recent=False)

            self.assertEqual(memory["source"], "LEGACY_UNKNOWN")
            self.assertEqual(memory["status"], "ACTIVE")
            self.assertEqual([item["key"] for item in recalled], ["project.legacy"])

    def test_memory_metadata_rejects_invalid_confidence_and_status(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(str(Path(directory) / "brain.db"))
            store.init()
            store.save_memory("project.validation", "metadata validation")

            with self.assertRaises(ValueError):
                store.set_memory_metadata("project.validation", confidence=float("nan"))
            with self.assertRaises(ValueError):
                store.set_memory_metadata("project.validation", confidence=1.5)
            with self.assertRaises(ValueError):
                store.set_memory_metadata("project.validation", status="MAGICALLY_VERIFIED")


    def test_recall_ranks_higher_confidence_evidence_first(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(str(Path(directory) / "brain.db"))
            store.init()
            store.save_memory("record.low_confidence", "deployment evidence verified")
            store.set_memory_metadata("record.low_confidence", source="test", confidence=0.1)
            store.save_memory("record.high_confidence", "deployment evidence verified")
            store.set_memory_metadata("record.high_confidence", source="test", confidence=0.95)

            recalled = store.recall_memories("deployment evidence", fallback_recent=False)

            self.assertEqual(recalled[0]["key"], "record.high_confidence")

    def test_unverified_memory_is_not_used_as_active_goal_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(str(Path(directory) / "brain.db"))
            store.init()
            store.save_memory("record.unverified", "deployment evidence verified")
            store.set_memory_metadata(
                "record.unverified", source="test", confidence=0.2, status="UNVERIFIED"
            )

            recalled = store.recall_memories("deployment evidence", fallback_recent=False)

            self.assertEqual(recalled, [])



if __name__ == "__main__":
    unittest.main()
