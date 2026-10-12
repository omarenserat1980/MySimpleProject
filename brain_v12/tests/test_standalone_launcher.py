"""Contract tests for the no-device standalone Brain launcher."""
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = REPO_ROOT / "brain_v12" / "tools" / "brain_standalone_launcher.sh"


class StandaloneLauncherContractTests(unittest.TestCase):
    def test_launcher_exists_and_starts_brain_api_directly(self):
        text = LAUNCHER.read_text(encoding="utf-8")
        self.assertIn("uvicorn brain_v12.mcp_server:app", text)
        self.assertIn('BRAIN_RUNTIME_HOME="${BRAIN_RUNTIME_HOME:-$HOME/.brain/runtime}"', text)
        self.assertIn('exec "$PYTHON" -m uvicorn', text)

    def test_launcher_does_not_require_devices_emulators_or_git_sync(self):
        text = LAUNCHER.read_text(encoding="utf-8").lower()
        forbidden = (
            "getprop",
            "redmi3-01",
            "realme-01",
            "brain_runtime_source_manager.sh",
            "git fetch",
            "v12_agent_id",
            "v12_agent_key_file",
            "device_bridge",
        )
        for marker in forbidden:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, text)

    def test_launcher_defaults_to_loopback_and_allows_explicit_host_override(self):
        text = LAUNCHER.read_text(encoding="utf-8")
        self.assertIn('HOST="${BRAIN_HOST:-127.0.0.1}"', text)
        self.assertIn('PORT="${PORT:-8012}"', text)


if __name__ == "__main__":
    unittest.main()
