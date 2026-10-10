import json
import unittest

from brain_v12.brain.quranic_reasoning_paths import (
    PATHWAYS,
    register_quranic_reasoning_paths,
    select_reasoning_path,
)


class InMemoryStore:
    def __init__(self):
        self.items = {}
        self.write_count = 0

    def memories(self):
        return [{"key": key, "value": value} for key, value in self.items.items()]

    def save_memory(self, key, value):
        self.write_count += 1
        self.items[key] = value


class QuranicReasoningPathTests(unittest.TestCase):
    def test_pathways_are_registered_with_sources_and_limits(self):
        store = InMemoryStore()
        keys = register_quranic_reasoning_paths(store)
        self.assertEqual(len(keys), len(PATHWAYS))
        self.assertEqual(len(keys), 8)
        self.assertEqual(len(store.items), len(PATHWAYS))
        for key in keys:
            record = json.loads(store.items[key])
            self.assertEqual(record["kind"], "reasoning_path")
            self.assertTrue(record["source_references"])
            self.assertTrue(record["stages"])
            self.assertIn("limits", record)
            self.assertEqual(
                record["epistemic_status"],
                "curated_application_not_literal_scriptural_algorithm",
            )

    def test_relevant_goal_selects_a_path_and_unrelated_goal_does_not(self):
        store = InMemoryStore()
        register_quranic_reasoning_paths(store)
        memories = store.memories()
        selected = select_reasoning_path("راجع ما أُنجز وقارن النتيجة بالهدف", memories)
        self.assertIsNotNone(selected)
        self.assertEqual(selected["key"], "reasoning_path.quranic.self_accountability")
        self.assertTrue(selected["source_references"])
        self.assertTrue(selected["stages"])
        self.assertIsNone(select_reasoning_path("طقس عمّان غدًا", memories))

    def test_registration_is_idempotent_without_rewriting_unchanged_records(self):
        store = InMemoryStore()
        first = register_quranic_reasoning_paths(store)
        snapshot = dict(store.items)
        initial_writes = store.write_count
        second = register_quranic_reasoning_paths(store)
        self.assertEqual(first, second)
        self.assertEqual(snapshot, store.items)
        self.assertEqual(store.write_count, initial_writes)


if __name__ == "__main__":
    unittest.main()
