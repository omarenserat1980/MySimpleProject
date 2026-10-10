import unittest
from pathlib import Path


class CloudRunnerIsolationContractTests(unittest.TestCase):
    def test_bootstrap_requires_dedicated_runner_identity(self):
        script = Path("tools/bootstrap_brain_cloud_executor.sh").read_text(encoding="utf-8")
        self.assertIn("DEDICATED_RUNNER_USER_REQUIRED", script)
        self.assertIn("OPERATOR_AND_RUNNER_ACCOUNTS_MUST_DIFFER", script)
        self.assertIn("OPERATOR_AND_RUNNER_HOMES_MUST_DIFFER", script)
        self.assertIn('RUNNER_GROUP="$(id -gn "$RUNNER_USER")"', script)
        self.assertIn("RUNNER_USER_MUST_BELONG_TO_KVM_GROUP", script)

    def test_runner_config_and_execution_use_isolated_home(self):
        script = Path("tools/bootstrap_brain_cloud_executor.sh").read_text(encoding="utf-8")
        isolated = 'sudo -u "$RUNNER_USER" -- env HOME="$RUNNER_HOME" RUNNER_ALLOW_RUNASROOT=0'
        self.assertIn(isolated + ' "$RUNNER_DIR/config.sh"', script)
        self.assertIn('STAGING_DIR="$(mktemp -d /tmp/brain-cloud-runner.XXXXXX)"', script)
        self.assertIn('sudo cp -a "$STAGING_DIR/." "$RUNNER_DIR/"', script)
        self.assertIn('rm -rf "$STAGING_DIR"\nSTAGING_DIR=""', script)
        self.assertIn('install -d -m 700 "$HOME/.local/state/brain"', script)
        self.assertNotIn('cd "$RUNNER_DIR"', script)
        self.assertIn(isolated + ' "$RUNNER_DIR/run.sh"', script)
        self.assertIn("unset TOKEN", script)
        self.assertIn("unset BRAIN_CLOUD_EXECUTOR_TOKEN", script)

    def test_runner_credential_boundary_is_checked_before_registration(self):
        script = Path("tools/bootstrap_brain_cloud_executor.sh").read_text(encoding="utf-8")
        self.assertIn('GH_CONFIG_DIR="${GH_CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/gh}"', script)
        self.assertIn('test ! -r "$GH_CONFIG_DIR" && test ! -x "$GH_CONFIG_DIR" && test ! -r "$GH_CONFIG_DIR/hosts.yml"', script)
        self.assertIn("RUNNER_CAN_READ_OPERATOR_GH_CREDENTIALS", script)
        self.assertIn("RUNNER_CANNOT_READ_OPERATOR_GH_CREDENTIALS=VERIFIED", script)
        self.assertIn("exit 40", script)
        self.assertLess(script.index("RUNNER_CANNOT_READ_OPERATOR_GH_CREDENTIALS=VERIFIED"),
                        script.index('"/repos/$REPO/actions/runners/registration-token"'))

    def test_runner_workspace_is_owned_by_runner_account(self):
        script = Path("tools/bootstrap_brain_cloud_executor.sh").read_text(encoding="utf-8")
        self.assertIn('sudo chown -R "$RUNNER_USER:$RUNNER_GROUP" "$RUNNER_DIR"', script)


if __name__ == "__main__":
    unittest.main()
