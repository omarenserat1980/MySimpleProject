from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
SHELL_SCRIPT = ROOT / "brain_v12" / "tools" / "brain-one.sh"
POWERSHELL_SCRIPT = ROOT / "brain_v12" / "tools" / "brain-one.ps1"


class BrainOneLineBootstrapTests(unittest.TestCase):
    def test_shell_bootstrap_exists_and_parses(self):
        self.assertTrue(SHELL_SCRIPT.is_file())
        if shutil.which("bash"):
            result = subprocess.run(
                ["bash", "-n", str(SHELL_SCRIPT)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_shell_bootstrap_is_fail_safe(self):
        content = SHELL_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("EXISTING_PATH_IS_NOT_A_GIT_REPOSITORY", content)
        self.assertIn("COMMAND_NAME_ALREADY_IN_USE", content)
        self.assertIn("Nothing was overwritten", content)
        self.assertNotIn("git reset --hard", content)
        self.assertNotIn("git clean -fd", content)
        self.assertNotIn("cat \"$HOME/v12-agent/agent.key\"", content)

    def test_windows_uses_wsl_and_does_not_fake_native_runtime(self):
        content = POWERSHELL_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("wsl.exe", content)
        self.assertIn("WSL_REQUIRED_FOR_WINDOWS_RUNTIME", content)
        self.assertIn("brain-one.sh", content)


if __name__ == "__main__":
    unittest.main()
