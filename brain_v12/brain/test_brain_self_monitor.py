import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from brain_v12.brain.brain_self_monitor import BrainSelfMonitor


class BrainSelfMonitorTests(unittest.TestCase):
    def make_layout(self, base):
        repo = Path(base)
        app = repo / "brain_v12"
        (app / "brain").mkdir(parents=True)
        (app / "brain_git").mkdir()
        (app / "brain" / "brain_supervisor.py").write_text("# fixture\n", encoding="utf-8")
        return repo, app

    @patch("brain_v12.brain.brain_self_monitor.subprocess.run")
    def test_accepts_repository_root(self, run):
        run.return_value = Mock(returncode=0, stdout="true\n", stderr="")
        with tempfile.TemporaryDirectory() as temp:
            repo, app = self.make_layout(temp)
            report = BrainSelfMonitor(repo).snapshot()

        self.assertTrue(report["ok"])
        self.assertEqual(report["status"], "HEALTHY")
        self.assertEqual(report["roots"]["repository"], str(repo))
        self.assertEqual(report["roots"]["application"], str(app))
        self.assertTrue(report["observed_at_utc"].endswith("+00:00"))
        run.assert_called_once()
        self.assertEqual(run.call_args.kwargs["cwd"], str(repo))
        self.assertEqual(run.call_args.kwargs["timeout"], 3)

    @patch("brain_v12.brain.brain_self_monitor.subprocess.run")
    def test_accepts_application_root_passed_by_app(self, run):
        run.return_value = Mock(returncode=0, stdout="true\n", stderr="")
        with tempfile.TemporaryDirectory() as temp:
            repo, app = self.make_layout(temp)
            report = BrainSelfMonitor(app).snapshot()

        self.assertTrue(report["ok"])
        self.assertEqual(report["roots"]["repository"], str(repo))
        self.assertEqual(report["roots"]["application"], str(app))
        self.assertEqual(run.call_args.kwargs["cwd"], str(repo))

    @patch("brain_v12.brain.brain_self_monitor.subprocess.run")
    def test_missing_canonical_file_reports_degraded(self, run):
        run.return_value = Mock(returncode=0, stdout="true\n", stderr="")
        with tempfile.TemporaryDirectory() as temp:
            repo, app = self.make_layout(temp)
            (app / "brain" / "brain_supervisor.py").unlink()
            report = BrainSelfMonitor(app).snapshot()

        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "DEGRADED")
        checks = {item["name"]: item for item in report["checks"]}
        self.assertFalse(checks["supervisor"]["ok"])
        self.assertTrue(checks["brain_root"]["ok"])

    @patch("brain_v12.brain.brain_self_monitor.subprocess.run", side_effect=TimeoutError("git timeout"))
    def test_git_timeout_is_reported_without_crashing(self, run):
        with tempfile.TemporaryDirectory() as temp:
            _, app = self.make_layout(temp)
            report = BrainSelfMonitor(app).snapshot()

        self.assertFalse(report["ok"])
        checks = {item["name"]: item for item in report["checks"]}
        self.assertFalse(checks["git_repository"]["ok"])
        self.assertIn("git timeout", checks["git_repository"]["detail"])


if __name__ == "__main__":
    unittest.main()
