import tempfile
import unittest
from pathlib import Path

from brain_v12.asic.unit_001.sqlite_evidence_store import ExperimentMemory


class ExperimentMemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ExperimentMemory(Path(self.tmp.name) / "brain.sqlite3")
        self.store.init()

    def tearDown(self):
        self.tmp.cleanup()

    def test_persists_across_reopen(self):
        saved = self.store.record({
            "project": "Electronic Brain", "subject": "realme-rmx3710",
            "event_type": "sha256d_reference_test", "status": "PASS",
            "environment": {"os": "Android 15", "arch": "aarch64"},
            "measurements": {"iterations": 10000, "hashes_per_second": 123.4},
            "evidence": ["bitcoin-genesis-header-reference-vector"],
            "limitations": ["not proof of mining", "not ASIC-equivalent performance"]
        })
        reopened = ExperimentMemory(self.store.db_path)
        self.assertEqual(reopened.get(saved["event_id"])["status"], "PASS")
        self.assertEqual(reopened.list_events(subject="realme-rmx3710")[0]["measurements"]["iterations"], 10000)

    def test_history_is_append_only_for_unique_events(self):
        for status in ("PASS", "FAIL"):
            self.store.record({"project": "Brain", "subject": "device-a",
                               "event_type": "test", "status": status})
        self.assertEqual(len(self.store.list_events(subject="device-a")), 2)

    def test_rejects_missing_required_fields(self):
        with self.assertRaises(ValueError):
            self.store.record({"subject": "device-a"})

    def test_rejects_secret_like_fields(self):
        with self.assertRaises(ValueError):
            self.store.record({"project": "Brain", "subject": "device-a",
                               "event_type": "test", "status": "PASS",
                               "environment": {"api_key": "should-not-persist"}})


if __name__ == "__main__":
    unittest.main()
