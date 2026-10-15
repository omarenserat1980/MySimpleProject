import unittest

from brain_v12.tools.github_actions_runtime_audit import build_report


class GitHubActionsRuntimeAuditTests(unittest.TestCase):
    def snapshot(self, conclusion=None):
        run = {"id": 12, "name": "Example", "path": ".github/workflows/example.yml",
               "conclusion": conclusion, "created_at": "2026-10-15T12:00:00Z",
               "html_url": "https://github.com/o/r/actions/runs/12"}
        return ({"complete": True, "workflows": [{"id": 1}]},
                {"complete": True, "workflow_runs": [run],
                 "window_start": "2026-10-14T12:00:00+00:00",
                 "window_end": "2026-10-15T12:00:00+00:00"})

    def test_successful_or_in_progress_runs_do_not_warn(self):
        for conclusion in ("success", None, "cancelled", "skipped"):
            with self.subTest(conclusion=conclusion):
                workflows, runs = self.snapshot(conclusion)
                report = build_report(workflows, runs)
                self.assertEqual(report["status"], "AUDITED")
                self.assertEqual(report["critical_warning_count"], 0)

    def test_critical_conclusions_produce_critical_warn(self):
        for conclusion in ("failure", "timed_out", "action_required", "startup_failure"):
            with self.subTest(conclusion=conclusion):
                workflows, runs = self.snapshot(conclusion)
                report = build_report(workflows, runs)
                self.assertEqual(report["status"], "CRITICAL_WARN")
                self.assertEqual(report["critical_warning_count"], 1)

    def test_incomplete_workflow_inventory_fails_closed(self):
        workflows, runs = self.snapshot("success")
        workflows["complete"] = False
        with self.assertRaisesRegex(ValueError, "WORKFLOW_INVENTORY_INCOMPLETE"):
            build_report(workflows, runs)

    def test_incomplete_run_inventory_fails_closed(self):
        workflows, runs = self.snapshot("success")
        runs["complete"] = False
        with self.assertRaisesRegex(ValueError, "WORKFLOW_RUN_INVENTORY_INCOMPLETE"):
            build_report(workflows, runs)

    def test_invalid_run_record_fails_closed(self):
        workflows, runs = self.snapshot("success")
        runs["workflow_runs"] = ["not-a-record"]
        with self.assertRaisesRegex(ValueError, "WORKFLOW_RUN_RECORD_INVALID"):
            build_report(workflows, runs)


if __name__ == "__main__":
    unittest.main()
