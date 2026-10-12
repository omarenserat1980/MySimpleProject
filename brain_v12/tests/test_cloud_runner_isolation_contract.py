import os
import shutil
import subprocess
import tempfile
import unittest
import uuid
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
        boundary_ok = script.index("RUNNER_CANNOT_READ_OPERATOR_GH_CREDENTIALS=VERIFIED")
        token_injection = script.index('TOKEN="$BRAIN_GITHUB_RUNNER_REGISTRATION_TOKEN"')
        runner_config = script.index('"$RUNNER_DIR/config.sh" --unattended')
        self.assertLess(boundary_ok, token_injection)
        self.assertLess(token_injection, runner_config)

    def test_credential_boundary_expression_with_real_unix_permissions(self):
        # GitHub-hosted Ubuntu runners provide passwordless sudo. On other
        # environments, retain the static contract tests without assuming root.
        if not shutil.which("sudo"):
            self.skipTest("sudo unavailable; real-identity permission test requires sudo")
        sudo = ["sudo", "-n"]
        if subprocess.run(sudo + ["true"], capture_output=True).returncode != 0:
            self.skipTest("passwordless sudo unavailable; real-identity permission test requires sudo")

        username = "brain-ci-" + uuid.uuid4().hex[:10]
        created = False
        try:
            subprocess.run(
                sudo + ["useradd", "--system", "--no-create-home", "--home-dir", "/nonexistent", username],
                check=True, capture_output=True, text=True,
            )
            created = True
            with tempfile.TemporaryDirectory(prefix="brain-gh-boundary-") as temp:
                # Make the parent traversable so this test measures the GH config ACL itself,
                # not TemporaryDirectory's default private parent directory.
                Path(temp).chmod(0o755)
                config_dir = Path(temp) / "gh"
                config_dir.mkdir(mode=0o700)
                hosts = config_dir / "hosts.yml"
                hosts.write_text("fixture-not-a-real-token\n", encoding="utf-8")
                hosts.chmod(0o600)
                config_dir.chmod(0o700)

                check = (
                    'test ! -r "$GH_CONFIG_DIR" && '
                    'test ! -x "$GH_CONFIG_DIR" && '
                    'test ! -r "$GH_CONFIG_DIR/hosts.yml"'
                )
                denied = subprocess.run(
                    sudo + ["-u", username, "--", "env",
                            "HOME=/nonexistent", "GH_CONFIG_DIR=" + str(config_dir),
                            "bash", "-c", check],
                    capture_output=True, text=True,
                )
                self.assertEqual(denied.returncode, 0, "private config should be unreadable by runner identity")

                # A deliberately permissive directory must make the same check fail.
                config_dir.chmod(0o755)
                hosts.chmod(0o644)
                allowed = subprocess.run(
                    sudo + ["-u", username, "--", "env",
                            "HOME=/nonexistent", "GH_CONFIG_DIR=" + str(config_dir),
                            "bash", "-c", check],
                    capture_output=True, text=True,
                )
                self.assertNotEqual(allowed.returncode, 0, "readable config must fail closed")
        finally:
            if created:
                subprocess.run(sudo + ["userdel", username], capture_output=True, text=True)

    def test_runner_workspace_is_owned_by_runner_account(self):
        script = Path("tools/bootstrap_brain_cloud_executor.sh").read_text(encoding="utf-8")
        self.assertIn('sudo chown -R "$RUNNER_USER:$RUNNER_GROUP" "$RUNNER_DIR"', script)


if __name__ == "__main__":
    unittest.main()
