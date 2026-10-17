import unittest

from brain_v12.brain.apm_build_report import build_report


class APMBuildReportTests(unittest.TestCase):
    def test_runner_waiting_is_resumable(self):
        r = build_report(completed=3, cached=2, runner_status="queued")
        self.assertEqual(r.status, "WAITING_FOR_RUNNER")
        self.assertEqual(r.next_action, "RESUME_WHEN_RUNNER_AVAILABLE")

    def test_failed_units_are_retried_only(self):
        r = build_report(completed=4, failed=1, runner_status="running")
        self.assertEqual(r.status, "FAILED")
        self.assertEqual(r.next_action, "RETRY_FAILED_UNITS_ONLY")

    def test_blocked_dependency_is_inspected(self):
        r = build_report(completed=4, blocked=1, runner_status="running")
        self.assertEqual(r.status, "BLOCKED")
        self.assertEqual(r.next_action, "INSPECT_BLOCKING_DEPENDENCY")


if __name__ == "__main__":
    unittest.main()
