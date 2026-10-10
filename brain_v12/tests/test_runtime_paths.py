import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain_v12.runtime_paths import configure_runtime_paths


class RuntimePathsTests(unittest.TestCase):
    def test_defaults_live_under_writable_runtime_home(self):
        names = (
            "BRAIN_DB",
            "BRAIN_SYNC_QUEUE",
            "BRAIN_GIT_ROOT",
            "BRAIN_EVIDENCE_DB",
            "BRAIN_MEDIA_ROOT",
        )
        with tempfile.TemporaryDirectory() as temporary:
            runtime_home = Path(temporary) / "brain-runtime"
            with patch.dict(os.environ, {"BRAIN_RUNTIME_HOME": str(runtime_home)}):
                for name in names:
                    os.environ.pop(name, None)
                resolved = configure_runtime_paths()
                self.assertEqual(resolved, runtime_home.resolve())
                self.assertTrue(resolved.is_dir())
                self.assertEqual(Path(os.environ["BRAIN_DB"]), resolved / "brain_v12.db")
                self.assertEqual(
                    Path(os.environ["BRAIN_SYNC_QUEUE"]),
                    resolved / "state" / "sync_queue.jsonl",
                )
                self.assertEqual(
                    Path(os.environ["BRAIN_GIT_ROOT"]), resolved / "brain_git_data"
                )
                self.assertEqual(
                    Path(os.environ["BRAIN_EVIDENCE_DB"]),
                    resolved / "brain6_artifacts" / "evidence" / "evidence.db",
                )
                self.assertEqual(
                    Path(os.environ["BRAIN_MEDIA_ROOT"]), resolved / "media"
                )

    def test_explicit_database_override_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            runtime_home = Path(temporary) / "brain-runtime"
            database = Path(temporary) / "custom.sqlite3"
            with patch.dict(
                os.environ,
                {
                    "BRAIN_RUNTIME_HOME": str(runtime_home),
                    "BRAIN_DB": str(database),
                },
            ):
                for name in (
                    "BRAIN_SYNC_QUEUE",
                    "BRAIN_GIT_ROOT",
                    "BRAIN_EVIDENCE_DB",
                    "BRAIN_MEDIA_ROOT",
                ):
                    os.environ.pop(name, None)
                configure_runtime_paths()
                self.assertEqual(os.environ["BRAIN_DB"], str(database))


if __name__ == "__main__":
    unittest.main()
