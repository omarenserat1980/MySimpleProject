import json
import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.run_evidence_store import (
    EvidenceConflict, EvidenceStoreError, RunEvidenceStore,
)


class RunEvidenceStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "evidence" / "runs.jsonl"
        self.store = RunEvidenceStore(self.path)

    def test_append_read_and_hash_chain(self):
        first = self.store.append(event_id="evt-1", task_id="task-1",
                                  event_type="QUEUED", payload={"detail": "safe"})
        second = self.store.append(event_id="evt-2", task_id="task-1",
                                   event_type="COMPLETED", payload={"exit_code": 0})
        self.assertEqual(first["sequence"], 1)
        self.assertEqual(second["previous_hash"], first["event_hash"])
        self.assertEqual(len(self.store.read_all()), 2)

    def test_identical_event_is_idempotent(self):
        args = dict(event_id="evt-1", task_id="task-1",
                    event_type="QUEUED", payload={"a": 1})
        self.store.append(**args)
        duplicate = self.store.append(**args)
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(len(self.store.read_all()), 1)

    def test_reused_event_id_with_different_content_fails(self):
        self.store.append(event_id="evt-1", task_id="task-1",
                          event_type="QUEUED", payload={"a": 1})
        with self.assertRaises(EvidenceConflict):
            self.store.append(event_id="evt-1", task_id="task-1",
                              event_type="FAILED", payload={"a": 2})

    def test_sensitive_fields_are_redacted(self):
        event = self.store.append(event_id="evt-1", task_id="task-1",
                                  event_type="QUEUED",
                                  payload={"access_token": "secret-value", "safe": "ok"})
        self.assertEqual(event["payload"]["access_token"], "[REDACTED]")
        self.assertNotIn("secret-value", self.path.read_text(encoding="utf-8"))

    def test_tampered_line_is_rejected(self):
        self.store.append(event_id="evt-1", task_id="task-1",
                          event_type="QUEUED", payload={"a": 1})
        line = json.loads(self.path.read_text(encoding="utf-8"))
        line["payload"]["a"] = 2
        self.path.write_text(json.dumps(line) + "\n", encoding="utf-8")
        with self.assertRaises(EvidenceStoreError):
            self.store.read_all()


if __name__ == "__main__":
    unittest.main()
