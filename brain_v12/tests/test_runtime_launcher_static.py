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
        self.assertIn('status = "CONNECTION_REFUSED"', source)
        self.assertNotIn("print(key)", source)
        self.assertNotIn("print(os.environ[\"BRAIN_AGENT_KEY\"])", source)

    def test_remote_endpoint_never_triggers_local_api_restart(self):
        source = LAUNCHER.read_text(encoding="utf-8")
        self.assertIn("is_local_api()", source)
        local_gate = source.find("if is_local_api; then")
        remote_branch = source.find("# A remote endpoint must never trigger launch/kill of the local API process.")
        restart = source.find("pkill -f '[u]vicorn brain_v12.app:app --host 127.0.0.1 --port 8012'")
        self.assertGreaterEqual(local_gate, 0)
        self.assertGreater(remote_branch, local_gate)
        self.assertGreater(restart, local_gate)
        self.assertGreater(remote_branch, restart, "local process kill must remain before remote-only branch")
        self.assertIn("REMOTE_API_UNREACHABLE", source)


if __name__ == "__main__":
    unittest.main()
