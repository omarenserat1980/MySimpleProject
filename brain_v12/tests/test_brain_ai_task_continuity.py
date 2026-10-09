import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain_v12.tools import brain_runtime_supervisor as supervisor


class BrainTaskContinuityTests(unittest.TestCase):
    def test_only_strictly_verified_completion_is_remembered(self):
        with tempfile.TemporaryDirectory() as tmp:
            history = Path(tmp) / "history.jsonl"
            rows = [
                {"event": "selected", "fingerprint": "goal:keep-working"},
                {"event": "completed", "fingerprint": "goal:old-contract", "verified": True},
                {"event": "completed", "fingerprint": "goal:verified", "verified": True,
                 "verification_contract": "strict-v1"},
                {"event": "completed", "fingerprint": "goal:failed", "verified": False,
                 "verification_contract": "strict-v1"},
            ]
            history.write_text(
                "".join(json.dumps(row) + "\n" for row in rows),
                encoding="utf-8",
            )
            with patch.object(supervisor, "HISTORY", history):
                self.assertEqual(supervisor.recent_fingerprints(), {"goal:verified"})

    def test_failed_objective_is_recovered_from_latest_journal_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            journal = root / "continuous_tasks.jsonl"
            rows = [
                {"task_id": "one", "fingerprint": "goal:original", "goal": "original objective",
                 "kind": "goal", "priority": 0.9, "status": "FAILED"},
                {"task_id": "two", "fingerprint": "goal:other", "goal": "other objective",
                 "kind": "goal", "priority": 0.5, "status": "RUNNING"},
                {"task_id": "three", "fingerprint": "goal:other", "goal": "other objective",
                 "kind": "goal", "priority": 0.5, "status": "VERIFIED"},
            ]
            journal.write_text(
                "".join(json.dumps(row) + "\n" for row in rows),
                encoding="utf-8",
            )
            with patch.object(supervisor, "STATE", root):
                pending = supervisor.pending_tracked_goals()
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0]["goal"], "original objective")

    def test_choose_goal_resumes_failed_objective_before_new_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            journal = root / "continuous_tasks.jsonl"
            journal.write_text(json.dumps({
                "task_id": "one", "fingerprint": "goal:original",
                "goal": "resume the original goal", "kind": "goal",
                "priority": 1.0, "status": "FAILED",
            }) + "\n", encoding="utf-8")
            with patch.object(supervisor, "STATE", root), patch.object(
                supervisor, "HISTORY", root / "history.jsonl"
            ), patch.object(
                supervisor, "candidates",
                return_value=[("health", 0.7, "unrelated new work")],
            ):
                self.assertEqual(
                    supervisor.choose_goal(),
                    ("goal", 1.0, "resume the original goal", "goal:original"),
                )

    def test_blocked_objective_is_parked_until_human_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "continuous_tasks.jsonl").write_text(json.dumps({
                "task_id": "blocked", "fingerprint": "goal:needs-approval",
                "goal": "needs approval", "kind": "goal",
                "priority": 1.0, "status": "BLOCKED",
            }) + "\n", encoding="utf-8")
            with patch.object(supervisor, "STATE", root), patch.object(
                supervisor, "HISTORY", root / "history.jsonl"
            ), patch.object(
                supervisor, "candidates",
                return_value=[
                    ("goal", 1.0, "needs approval"),
                    ("health", 0.7, "safe health review"),
                ],
            ):
                self.assertEqual(
                    supervisor.choose_goal(),
                    ("health", 0.7, "safe health review", "health:safe health review"),
                )



if __name__ == "__main__":
    unittest.main()
