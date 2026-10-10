"""Static safety checks for the Termux Brain runtime launcher."""
from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / "brain_v12" / "tools" / "brain_runtime_launcher.sh"


class RuntimeLauncherStaticTests(unittest.TestCase):
    def test_launcher_uses_bash_syntax(self):
        bash = shutil.which("bash")
        if not bash:
            self.skipTest("bash is not installed on this platform")
        result = subprocess.run(
            [bash, "-n", str(LAUNCHER)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_explicit_v12_url_is_preserved_after_paid_endpoint_guards(self):
        source = LAUNCHER.read_text(encoding="utf-8")
        guard_pos = source.find('if [[ "${V12_BRAIN_URL:-}" == *render.com* ]]')
        assignment_pos = source.find(
            'export V12_BRAIN_URL="${V12_BRAIN_URL:-${BRAIN_URL:-http://127.0.0.1:8012}}"'
        )
        self.assertGreaterEqual(guard_pos, 0, "Render endpoint guard missing")
        self.assertGreater(assignment_pos, guard_pos, "URL assignment must follow endpoint guards")

    def test_auth_diagnostics_do_not_log_key_material(self):
        source = LAUNCHER.read_text(encoding="utf-8")
        self.assertIn("auth_diagnostic()", source)
        self.assertIn("JET_BRAIN_AUTH_DIAGNOSTIC status=HTTP_", source)
        self.assertIn("JET_BRAIN_AUTH_DIAGNOSTIC status=CONNECTION_REFUSED", source)
        self.assertNotIn("print(key)", source)
        self.assertNotIn("print(os.environ[\"BRAIN_AGENT_KEY\"])", source)


if __name__ == "__main__":
    unittest.main()
