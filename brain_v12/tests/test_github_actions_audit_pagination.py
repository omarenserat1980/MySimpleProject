import unittest
from datetime import datetime, timezone, timedelta

from brain_v12.github_control_plane import GitHubControlPlane, GitHubControlError


class FakeControlPlane(GitHubControlPlane):
    def __init__(self, responses):
        super().__init__(token="test-token")
        self.responses = responses
        self.calls = []

    def request(self, method, path, *, capability="repo.read", approved=False,
                params=None, body=None, timeout=30.0):
        self.calls.append((method, path, params))
        key = (path, (params or {}).get("page", 1))
        value = self.responses.get(key)
        if isinstance(value, Exception):
            raise value
        if value is None:
            raise AssertionError(f"Unexpected request: {key}")
        return value


class GitHubActionsAuditPaginationTests(unittest.TestCase):
    def test_workflow_definitions_are_paginated_until_short_page(self):
        path = "/repos/o/r/actions/workflows"
        api = FakeControlPlane({
            (path, 1): {"workflows": [{"id": i} for i in range(100)]},
            (path, 2): {"workflows": [{"id": 100}]},
        })
        result = api.actions_workflows_all("o", "r")
        self.assertTrue(result["complete"])
        self.assertEqual(result["count"], 101)
        self.assertEqual(result["pages_fetched"], 2)

    def test_recent_runs_cover_all_pages_and_report_window(self):
        path = "/repos/o/r/actions/runs"
        now = datetime(2026, 10, 15, 12, tzinfo=timezone.utc)
        old = (now - timedelta(hours=25)).isoformat().replace("+00:00", "Z")
        recent = (now - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
        api = FakeControlPlane({
            (path, 1): {"total_count": 2, "workflow_runs": [{"id": 1, "created_at": recent}]},
            (path, 2): {"total_count": 2, "workflow_runs": [{"id": 2, "created_at": old}]},
        })
        result = api.actions_runs_last_24h("o", "r", now=now, per_page=1)
        self.assertTrue(result["complete"])
        self.assertEqual([r["id"] for r in result["workflow_runs"]], [1])
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["pages_fetched"], 2)

    def test_api_cap_is_blocked_not_reported_as_complete(self):
        path = "/repos/o/r/actions/runs"
        api = FakeControlPlane({
            (path, 1): {"total_count": 1001, "workflow_runs": []},
        })
        with self.assertRaisesRegex(GitHubControlError, "ACTIONS_RUNS_API_RESULT_CAP_EXCEEDED"):
            api.actions_runs_last_24h("o", "r", now=datetime.now(timezone.utc))

    def test_missing_total_count_fails_closed(self):
        path = "/repos/o/r/actions/runs"
        api = FakeControlPlane({
            (path, 1): {"workflow_runs": []},
        })
        with self.assertRaisesRegex(GitHubControlError, "ACTIONS_RUNS_TOTAL_COUNT_MISSING"):
            api.actions_runs_last_24h("o", "r", now=datetime.now(timezone.utc))

    def test_naive_clock_is_rejected(self):
        api = FakeControlPlane({})
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            api.actions_runs_last_24h("o", "r", now=datetime(2026, 10, 15, 12))


if __name__ == "__main__":
    unittest.main()
