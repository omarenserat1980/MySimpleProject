import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain_v12.runtime_paths import configure_runtime_paths


PATH_VARIABLES = (
    "BRAIN_RUNTIME_HOME",
    "BRAIN_DB",
    "BRAIN_SYNC_QUEUE",
    "BRAIN_GIT_ROOT",
    "BRAIN_EVIDENCE_DB",
    "BRAIN_MEDIA_ROOT",
    "BRAIN_MEDIA_OUTPUT_ROOT",
)


def create_db(path: Path, table: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.execute(f"CREATE TABLE {table} (value TEXT NOT NULL)")
        db.execute(f"INSERT INTO {table}(value) VALUES (?)", (f"legacy-{table}",))


class RuntimePathsTests(unittest.TestCase):
    def test_default_paths_migrate_legacy_state_without_deleting_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            runtime_home = root / "runtime"
            source.mkdir()

            legacy_db = source / "brain_v12.db"
            legacy_evidence = source / "brain6_artifacts" / "evidence" / "evidence.db"
            create_db(legacy_db, "brain_state")
            create_db(legacy_evidence, "evidence_state")

            legacy_queue = source / ".brain" / "state" / "sync_queue.jsonl"
            legacy_queue.parent.mkdir(parents=True)
            legacy_queue.write_text('{"event":"legacy"}\n', encoding="utf-8")
            legacy_workflows = source / "brain_git_data" / "workflows"
            legacy_workflows.mkdir(parents=True)
            (legacy_workflows / "legacy.json").write_text("legacy-workflow", encoding="utf-8")
            legacy_media = source / "web" / "media"
            legacy_media.mkdir(parents=True)
            (legacy_media / "existing.mp4").write_bytes(b"existing-media")

            with patch.dict(os.environ, {"BRAIN_RUNTIME_HOME": str(runtime_home)}, clear=True):
                resolved = configure_runtime_paths(source_root=source)

                self.assertEqual(resolved, runtime_home.resolve())
                self.assertEqual(Path(os.environ["BRAIN_DB"]), runtime_home / "brain_v12.db")
                self.assertEqual(
                    Path(os.environ["BRAIN_SYNC_QUEUE"]),
                    runtime_home / "state" / "sync_queue.jsonl",
                )
                self.assertEqual(
                    Path(os.environ["BRAIN_GIT_ROOT"]), runtime_home / "brain_git_data"
                )
                self.assertEqual(
                    Path(os.environ["BRAIN_EVIDENCE_DB"]),
                    runtime_home / "brain6_artifacts" / "evidence" / "evidence.db",
                )
                runtime_media = runtime_home / "media"
                self.assertEqual(Path(os.environ["BRAIN_MEDIA_ROOT"]), runtime_media.resolve())
                self.assertEqual((runtime_media / "existing.mp4").read_bytes(), b"existing-media")
                self.assertEqual(
                    Path(os.environ["BRAIN_MEDIA_OUTPUT_ROOT"]),
                    runtime_home / "media" / "engine",
                )

                with sqlite3.connect(os.environ["BRAIN_DB"]) as db:
                    self.assertEqual(db.execute("SELECT value FROM brain_state").fetchone()[0], "legacy-brain_state")
                with sqlite3.connect(os.environ["BRAIN_EVIDENCE_DB"]) as db:
                    self.assertEqual(db.execute("SELECT value FROM evidence_state").fetchone()[0], "legacy-evidence_state")

                self.assertEqual(
                    Path(os.environ["BRAIN_SYNC_QUEUE"]).read_text(encoding="utf-8"),
                    '{"event":"legacy"}\n',
                )
                self.assertEqual(
                    (Path(os.environ["BRAIN_GIT_ROOT"]) / "workflows" / "legacy.json").read_text(),
                    "legacy-workflow",
                )
                self.assertTrue((Path(os.environ["BRAIN_MEDIA_ROOT"]) / "existing.mp4").is_file())
                self.assertTrue((legacy_media / "existing.mp4").is_file())

            # Migration is copy-only: every original state source remains available.
            self.assertTrue(legacy_db.is_file())
            self.assertTrue(legacy_evidence.is_file())
            self.assertTrue(legacy_queue.is_file())
            self.assertTrue((legacy_workflows / "legacy.json").is_file())

    def test_explicit_database_override_is_preserved_and_not_seeded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            legacy_db = source / "brain_v12.db"
            create_db(legacy_db, "brain_state")
            custom_db = root / "custom.sqlite3"
            runtime_home = root / "runtime"

            with patch.dict(
                os.environ,
                {"BRAIN_RUNTIME_HOME": str(runtime_home), "BRAIN_DB": str(custom_db)},
                clear=True,
            ):
                configure_runtime_paths(source_root=source)
                self.assertEqual(os.environ["BRAIN_DB"], str(custom_db))
                self.assertFalse(custom_db.exists())
                self.assertTrue(legacy_db.exists())

    def test_existing_destination_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            runtime_home = root / "runtime"
            source.mkdir()
            create_db(source / "brain_v12.db", "brain_state")
            runtime_home.mkdir()
            existing_db = runtime_home / "brain_v12.db"
            with sqlite3.connect(existing_db) as db:
                db.execute("CREATE TABLE chosen (value TEXT)")
                db.execute("INSERT INTO chosen(value) VALUES ('runtime-wins')")

            with patch.dict(os.environ, {"BRAIN_RUNTIME_HOME": str(runtime_home)}, clear=True):
                configure_runtime_paths(source_root=source)
                with sqlite3.connect(existing_db) as db:
                    self.assertEqual(db.execute("SELECT value FROM chosen").fetchone()[0], "runtime-wins")


if __name__ == "__main__":
    unittest.main()
