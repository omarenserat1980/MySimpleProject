import tempfile
import unittest
from pathlib import Path

from brain_v12.asic.unit_001.sqlite_evidence_store import ExperimentMemory
from brain_v12.asic.unit_001.task_evidence import TaskEvidenceRunner


class TaskEvidenceRunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.memory = ExperimentMemory(Path(self.tmp.name) / "events.sqlite3")
        self.memory.init()
        self.runner = TaskEvidenceRunner(self.memory)

    def test_success_is_recorded_and_return_value_preserved(self):
        value = self.runner.run(
            lambda: 42, project="test-project", subject="unit-test",
            task_name="returns-42",
        )
        self.assertEqual(value, 42)
        events = self.memory.list_events(subject="unit-test")
        self.assertEqual({e["status"] for e in events}, {"STARTED", "SUCCEEDED"})
        self.assertEqual(len({e["measurements"]["run_id"] for e in events}), 1)

    def test_failure_is_recorded_and_exception_reraised(self):
        def fail():
            raise RuntimeError("sensitive details should not be stored")

        with self.assertRaisesRegex(RuntimeError, "sensitive details"):
            self.runner.run(
                fail, project="test-project", subject="failure-test",
                task_name="raises",
            )
        events = self.memory.list_events(subject="failure-test")
        self.assertEqual({e["status"] for e in events}, {"STARTED", "FAILED"})
        failed = next(e for e in events if e["status"] == "FAILED")
        self.assertEqual(failed["measurements"]["exception_type"], "RuntimeError")
        self.assertNotIn("sensitive details", str(failed))

    def test_recent_returns_prior_events_for_planning(self):
        self.runner.run(
            lambda: None, project="test-project", subject="planning-test",
            task_name="prior-task",
        )
        prior = self.runner.recent("planning-test")
        self.assertEqual(len(prior), 2)
        self.assertTrue(all(e["subject"] == "planning-test" for e in prior))


if __name__ == "__main__":
    unittest.main()
