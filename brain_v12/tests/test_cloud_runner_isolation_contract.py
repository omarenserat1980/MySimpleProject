import unittest
from pathlib import Path


class CloudRunnerIsolationContractTests(unittest.TestCase):
    def test_bootstrap_requires_dedicated_runner_identity(self):
        script = Path("tools/bootstrap_brain_cloud_executor.sh").read_text(encoding="utf-8")
        self.assertIn("DEDICATED_RUNNER_USER_REQUIRED", script)
        self.assertIn("OPERATOR_AND_RUNNER_ACCOUNTS_MUST_DIFFER", script)
        self.assertIn("RUNNER_USER_MUST_BELONG_TO_KVM_GROUP", script)

    def test_runner_config_and_execution_use_isolated_home(self):
        script = Path("tools/bootstrap_brain_cloud_executor.sh").read_text(encoding="utf-8")
        isolated = 'sudo -u "$RUNNER_USER" -- env HOME="$RUNNER_HOME" RUNNER_ALLOW_RUNASROOT=0'
        self.assertIn(isolated + " ./config.sh", script)
        self.assertIn(isolated + " ./run.sh", script)
        self.assertIn("unset TOKEN", script)
        self.assertIn("unset BRAIN_CLOUD_EXECUTOR_TOKEN", script)

    def test_runner_workspace_is_owned_by_runner_account(self):
        script = Path("tools/bootstrap_brain_cloud_executor.sh").read_text(encoding="utf-8")
        self.assertIn('sudo chown -R "$RUNNER_USER:$RUNNER_USER" "$RUNNER_DIR"', script)


if __name__ == "__main__":
    unittest.main()
