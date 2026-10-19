import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.follow_up_store import FollowUpStore


class FollowUpStoreTests(unittest.TestCase):
    def test_seeded_ledger_persists_and_summarizes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "follow-up.sqlite3"
            first = FollowUpStore(path)
            self.assertEqual(first.summary()["storage"], "sqlite")
            self.assertEqual(first.get_task("TRACK-007")["status"], "BLOCKED")
            first.update_task(
                "TRACK-005",
                status="IN_PROGRESS",
                note="API implementation under test",
                evidence=["https://example.invalid/run/123"],
            )
            second = FollowUpStore(path)
            self.assertEqual(second.get_task("TRACK-005")["status"], "IN_PROGRESS")
            self.assertEqual(second.summary()["active_tasks"], 1)

    def test_pass_requires_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            store = FollowUpStore(Path(directory) / "follow-up.sqlite3")
            with self.assertRaisesRegex(ValueError, "PASS_REQUIRES_EVIDENCE"):
                store.update_task("TRACK-005", status="PASS", note="looks good")

    def test_invalid_status_and_missing_task_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            store = FollowUpStore(Path(directory) / "follow-up.sqlite3")
            with self.assertRaisesRegex(ValueError, "INVALID_STATUS"):
                store.update_task("TRACK-005", status="DONE", note="invalid")
            with self.assertRaisesRegex(KeyError, "TASK_NOT_FOUND"):
                store.update_task("NO-SUCH-TASK", status="IN_PROGRESS", note="missing")

    def test_every_update_is_audited(self):
        with tempfile.TemporaryDirectory() as directory:
            store = FollowUpStore(Path(directory) / "follow-up.sqlite3")
            store.update_task(
                "TRACK-005",
                status="IN_PROGRESS",
                note="Started implementation",
                evidence=["https://example.invalid/commit/abc"],
            )
            history = store.history("TRACK-005")
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["previous_status"], "IN_PROGRESS")
            self.assertEqual(history[0]["new_status"], "IN_PROGRESS")
            self.assertEqual(history[0]["evidence"], ["https://example.invalid/commit/abc"])


if __name__ == "__main__":
    unittest.main()
