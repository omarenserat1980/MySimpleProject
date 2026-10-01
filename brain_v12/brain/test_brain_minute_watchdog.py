import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain_v12.brain import brain_minute_watchdog as w


class MinuteWatchdogTests(unittest.TestCase):
    def test_classification_only_accepts_completed_failures(self):
        self.assertEqual(
            w.classify({"status": "completed", "conclusion": "failure"}),
            "FAILED_OR_TIMED_OUT",
        )
        self.assertEqual(
            w.classify({"status": "in_progress", "conclusion": None}),
            "OTHER",
        )

    def test_inspect_reruns_failed_run_once(self):
        with tempfile.TemporaryDirectory() as d:
            state = Path(d) / "state.json"
            log = Path(d) / "watchdog.log"
            state.write_text(json.dumps({"seen": {}, "updated_at": None}), encoding="utf-8")
            w.STATE = state
            w.LOG = log

            payload = json.dumps([{
                "databaseId": 123,
                "status": "completed",
                "conclusion": "failure",
                "workflowName": "Brain Windows Real Boot Evidence",
                "attempt": 1,
                "headSha": "abc",
                "updatedAt": "2026-10-01T00:00:00Z",
            }])

            calls = []
            with patch.object(w, "run_gh", side_effect=lambda *args: calls.append(args) or payload):
                w.inspect_once()

            self.assertTrue(any("rerun" in c for c in calls))
            saved = json.loads(state.read_text(encoding="utf-8"))
            self.assertEqual(saved["seen"]["123:1"]["action"], "RERUN_FAILED_JOBS")

    def test_max_attempts_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            state = Path(d) / "state.json"
            log = Path(d) / "watchdog.log"
            state.write_text(json.dumps({"seen": {}, "updated_at": None}), encoding="utf-8")
            w.STATE = state
            w.LOG = log

            payload = json.dumps([{
                "databaseId": 456,
                "status": "completed",
                "conclusion": "timed_out",
                "workflowName": "Brain Virtual Computer",
                "attempt": 3,
                "headSha": "def",
                "updatedAt": "2026-10-01T00:00:00Z",
            }])

            calls = []
            with patch.object(w, "run_gh", side_effect=lambda *args: calls.append(args) or payload):
                w.inspect_once()

            self.assertFalse(any("rerun" in c for c in calls))
            saved = json.loads(state.read_text(encoding="utf-8"))
            self.assertEqual(saved["seen"]["456:3"]["action"], "BLOCKED_MAX_ATTEMPTS")


if __name__ == "__main__":
    unittest.main()
