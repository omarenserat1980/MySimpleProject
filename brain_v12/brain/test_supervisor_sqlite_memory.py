"""Integration tests for supervisor-backed SQLite task memory."""
import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.brain_supervisor import BrainSupervisor


class SupervisorSQLiteMemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_plan_reads_previous_same_task_history_without_storing_prompt(self):
        task = "repeatable memory integration check"
        first = BrainSupervisor(root=self.root)
        first_job = first.create(task)
        first.transition(first_job, "plan", enforce_authority=False)
        self.assertTrue(first.task_history(task))
        stored = str(first.experiment_memory.list_events(subject=first._task_subject(task)))
        self.assertNotIn(task, stored)

        second = BrainSupervisor(root=self.root)
        second_job = second.create(task)
        planned = second.transition(second_job, "plan", enforce_authority=False)
        history = planned.get("prior_task_history", [])
        self.assertTrue(history)
        self.assertTrue(any(item.get("phase") == "plan" for item in history))
        self.assertTrue(all(item.get("job_id") != second_job["job_id"] for item in history))
        # Prior history must be part of the checkpointed job details, not only
        # attached to the return value after persistence.
        self.assertEqual(planned.get("details", {}).get("prior_task_history"), history)
        persisted_jobs = second.control.jobs
        persisted = next(item for item in persisted_jobs if item.get("job_id") == second_job["job_id"])
        self.assertEqual(persisted.get("details", {}).get("prior_task_history"), history)

    def test_reasoning_receives_prior_task_history_as_context(self):
        task = "reasoning context persistence check"
        brain = BrainSupervisor(root=self.root)
        first = brain.create(task)
        brain.transition(first, "plan", enforce_authority=False)
        second = brain.create(task)

        decision = brain.reason({
            "job_id": second["job_id"],
            "failures": [{"class": "CODE_OR_LOGIC", "id": "test-failure"}],
            "attempts": 0,
            "max_attempts": 3,
        })

        self.assertIn("prior_task_history_events=", decision.reason)
        self.assertIn("prior_blocked_or_failed=", decision.reason)
        self.assertEqual(decision.action, "repair")

    def test_distinct_task_has_separate_history_subject(self):
        brain = BrainSupervisor(root=self.root)
        job = brain.create("task alpha")
        brain.transition(job, "plan", enforce_authority=False)
        self.assertTrue(brain.task_history("task alpha"))
        self.assertEqual(brain.task_history("task beta"), [])


if __name__ == "__main__":
    unittest.main()
