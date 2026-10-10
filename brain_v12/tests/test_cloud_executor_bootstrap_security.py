"""Regression checks for cloud-runner credential isolation."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP = ROOT / "tools" / "bootstrap_brain_cloud_executor.sh"


class CloudExecutorBootstrapSecurityTests(unittest.TestCase):
    def test_bootstrap_does_not_read_persisted_gh_credentials(self):
        script = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertNotIn("gh api", script)
        self.assertNotIn("gh auth status", script)
        self.assertIn("GITHUB_RUNNER_REGISTRATION_TOKEN_REQUIRED", script)

    def test_registration_token_is_cleared_before_runner_job(self):
        script = BOOTSTRAP.read_text(encoding="utf-8")
        unset_at = script.index("unset BRAIN_GITHUB_RUNNER_REGISTRATION_TOKEN")
        config_at = script.index("./config.sh --unattended")
        token_unset_at = script.index("unset TOKEN", config_at)
        run_at = script.index('exec ./run.sh')
        self.assertLess(unset_at, config_at)
        self.assertLess(token_unset_at, run_at)

    def test_bootstrap_refuses_root_execution(self):
        script = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("CLOUD_EXECUTOR_UNPRIVILEGED_ACCOUNT_REQUIRED", script)
        self.assertIn('[ "$(id -u)" -ne 0 ]', script)

    def test_runner_is_ephemeral(self):
        script = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("--ephemeral", script)
        self.assertIn("exec ./run.sh", script)


if __name__ == "__main__":
    unittest.main()
