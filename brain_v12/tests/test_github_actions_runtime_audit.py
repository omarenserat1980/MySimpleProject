import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from brain_v12.github_control_plane import GitHubControlPlane, GitHubControlError

from brain_v12.tools.github_actions_runtime_audit import build_report, safe_error_code


class GitHubActionsRuntimeAuditTests(unittest.TestCase):
    def snapshot(self, conclusion=None):
        run = {"id": 12, "name": "Example", "path": ".github/workflows/example.yml",
               "conclusion": conclusion, "created_at": "2026-10-15T12:00:00Z",
               "html_url": "https://github.com/o/r/actions/runs/12"}
        return ({"complete": True, "workflows": [{"id": 1}]},
                {"complete": True, "workflow_runs": [run],
                 "window_start": "2026-10-14T12:00:00+00:00",
                 "window_end": "2026-10-15T12:00:00+00:00"})


    def test_run_audit_paginates_per_workflow_beyond_repo_wide_cap(self):
        api = GitHubControlPlane(token="test")
        now = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)
        def fake_request(method, path, *, capability, params):
            self.assertIn("/actions/workflows/", path)
            workflow_id = int(path.split("/actions/workflows/")[1].split("/")[0])
            page = params["page"]
            if workflow_id == 10 and page == 1:
                return {"total_count": 101, "workflow_runs": [
                    {"id": i, "created_at": "2026-10-15T11:00:00Z", "conclusion": "success"}
                    for i in range(100)
                ]}
            if workflow_id == 10 and page == 2:
                return {"total_count": 101, "workflow_runs": [
                    {"id": 101, "created_at": "2026-10-15T11:00:00Z", "conclusion": "success"}
                ]}
            if workflow_id == 20 and page == 1:
                return {"total_count": 1, "workflow_runs": [
                    {"id": 201, "created_at": "2026-10-15T10:00:00Z", "conclusion": "failure"}
                ]}
            raise AssertionError(f"Unexpected request: {path} page={page}")
        with patch.object(api, "request", side_effect=fake_request):
            result = api.actions_runs_last_24h("owner", "repo", workflow_ids=[10, 20], now=now)
        self.assertTrue(result["complete"])
        self.assertEqual(result["count"], 102)
        self.assertEqual(result["api_total_count"], 102)
        self.assertEqual(result["pages_fetched"], 3)

    def test_run_audit_still_fails_closed_if_one_workflow_exceeds_api_cap(self):
        api = GitHubControlPlane(token="test")
        now = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)
        with patch.object(api, "request", return_value={"total_count": 1001, "workflow_runs": []}):
            with self.assertRaisesRegex(GitHubControlError, "ACTIONS_RUNS_API_RESULT_CAP_EXCEEDED"):
                api.actions_runs_last_24h("owner", "repo", workflow_ids=[10], now=now)

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

    def test_error_code_does_not_leak_api_response_body(self):
        exc = RuntimeError("GITHUB_HTTP_403:token=ghp_secret response body")
        self.assertEqual(safe_error_code(exc), "GITHUB_HTTP_403")
        self.assertNotIn("ghp_secret", safe_error_code(exc))

    def test_unknown_error_does_not_copy_exception_message(self):
        exc = RuntimeError("private response details and credentials")
        self.assertEqual(safe_error_code(exc), "RuntimeError")


if __name__ == "__main__":
    unittest.main()
