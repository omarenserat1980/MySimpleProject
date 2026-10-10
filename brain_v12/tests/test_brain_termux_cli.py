from pathlib import Path
import unittest
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "brain"

class BrainTermuxCliContractTests(unittest.TestCase):
    def test_shell_syntax_is_valid(self):
        result = subprocess.run(["bash", "-n", str(CLI)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_cli_has_single_command_surface(self):
        text = CLI.read_text(encoding="utf-8")
        for command in ("install", "start", "status", "diagnose", "logs"):
            self.assertIn(command, text)

    def test_start_delegates_to_existing_bootstrap(self):
        text = CLI.read_text(encoding="utf-8")
        self.assertIn('bash "$BOOTSTRAP"', text)
        self.assertIn("NONCANONICAL_REPOSITORY_PATH", text)

    def test_install_refuses_to_overwrite_unrelated_command(self):
        text = CLI.read_text(encoding="utf-8")
        self.assertIn("COMMAND_NAME_ALREADY_IN_USE", text)
        self.assertIn("Nothing was overwritten", text)

    def test_cli_never_reads_or_prints_secret_contents(self):
        text = CLI.read_text(encoding="utf-8")
        self.assertNotIn('cat "$HOME/v12-agent/agent.key"', text)
        self.assertNotIn('cat "$HOME/.brain_env"', text)
        self.assertIn("secrets_printed=false", text)
        self.assertIn("agent_key_file=present", text)

if __name__ == "__main__":
    unittest.main()
