import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain_v12.runtime_paths import configure_runtime_paths
from brain_v12.brain.durable_task_store import DurableTaskStore
from brain_v12.brain.evidence_store import EvidenceStore
from brain_v12.brain.virtual_task_queue import VirtualTaskQueue
from unittest.mock import MagicMock


PATH_VARIABLES = (
    "BRAIN_RUNTIME_HOME",
    "BRAIN_DB",
    "BRAIN_SYNC_QUEUE",
    "BRAIN_GIT_ROOT",
    "BRAIN_EVIDENCE_DB",
    "BRAIN_MEDIA_ROOT",
    "BRAIN_MEDIA_OUTPUT_ROOT",
    "AGENT_SANDBOX",
    "BRAIN_SUPERVISOR_ROOT",
    "BRAIN_SUCCESS_BOT_ROOT",
    "BRAIN_VIRTUAL_TASK_DB",
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
            legacy_sandbox = source.parent / "agent_sandbox"
            legacy_sandbox.mkdir()
            (legacy_sandbox / "existing.txt").write_text("legacy-sandbox", encoding="utf-8")
            legacy_supervisor = source.parent / "brain6_artifacts" / "supervisor"
            legacy_supervisor.mkdir(parents=True)
            (legacy_supervisor / "state.json").write_text("legacy-supervisor", encoding="utf-8")
            legacy_success_bot = source.parent / "brain6_artifacts" / "success_bot"
            legacy_success_bot.mkdir(parents=True)
            (legacy_success_bot / "state.json").write_text("legacy-success-bot", encoding="utf-8")
            legacy_virtual_tasks = source.parent / "brain6_artifacts" / "virtual_tasks" / "tasks.db"
            create_db(legacy_virtual_tasks, "virtual_tasks")

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
                self.assertEqual(Path(os.environ["AGENT_SANDBOX"]), runtime_home / "agent_sandbox")
                self.assertEqual(
                    (runtime_home / "agent_sandbox" / "existing.txt").read_text(encoding="utf-8"),
                    "legacy-sandbox",
                )
                self.assertEqual(
                    Path(os.environ["BRAIN_SUPERVISOR_ROOT"]),
                    runtime_home / "brain6_artifacts" / "supervisor",
                )
                self.assertEqual(
                    (runtime_home / "brain6_artifacts" / "supervisor" / "state.json").read_text(encoding="utf-8"),
                    "legacy-supervisor",
                )
                self.assertEqual(
                    Path(os.environ["BRAIN_SUCCESS_BOT_ROOT"]),
                    runtime_home / "brain6_artifacts" / "success_bot",
                )
                self.assertEqual(
                    (runtime_home / "brain6_artifacts" / "success_bot" / "state.json").read_text(encoding="utf-8"),
                    "legacy-success-bot",
                )
                self.assertEqual(
                    Path(os.environ["BRAIN_VIRTUAL_TASK_DB"]),
                    runtime_home / "brain6_artifacts" / "virtual_tasks" / "tasks.db",
                )
                with sqlite3.connect(os.environ["BRAIN_VIRTUAL_TASK_DB"]) as db:
                    self.assertEqual(
                        db.execute("SELECT value FROM virtual_tasks").fetchone()[0],
                        "legacy-virtual_tasks",
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
            self.assertTrue((legacy_sandbox / "existing.txt").is_file())
            self.assertTrue((legacy_supervisor / "state.json").is_file())
            self.assertTrue((legacy_success_bot / "state.json").is_file())
            self.assertTrue(legacy_virtual_tasks.is_file())

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

    def test_durable_task_store_default_uses_runtime_home(self):
        with tempfile.TemporaryDirectory() as temporary:
            runtime_home = Path(temporary) / "runtime"
            with patch.dict(os.environ, {"BRAIN_RUNTIME_HOME": str(runtime_home)}, clear=True):
                store = DurableTaskStore()
                try:
                    self.assertEqual(
                        store.path,
                        runtime_home / "brain6_artifacts" / "virtual_tasks" / "tasks.db",
                    )
                    self.assertTrue(store.path.is_file())
                finally:
                    store.close()

    def test_virtual_task_queue_passes_default_store_path_through(self):
        store_mock = MagicMock()
        with tempfile.TemporaryDirectory() as temporary:
            runtime_home = Path(temporary) / "runtime"
            with patch.dict(os.environ, {"BRAIN_RUNTIME_HOME": str(runtime_home)}, clear=True):
                with patch("brain_v12.brain.virtual_task_queue.DurableTaskStore", return_value=store_mock) as factory:
                    queue = VirtualTaskQueue(chassis=MagicMock(), resource_manager=MagicMock())
                    try:
                        factory.assert_called_once_with(
                            runtime_home / "brain6_artifacts" / "virtual_tasks" / "tasks.db"
                        )
                    finally:
                        queue.shutdown()

    def test_evidence_store_default_uses_runtime_home(self):
        with tempfile.TemporaryDirectory() as temporary:
            runtime_home = Path(temporary) / "runtime"
            with patch.dict(os.environ, {"BRAIN_RUNTIME_HOME": str(runtime_home)}, clear=True):
                store = EvidenceStore()
                try:
                    self.assertEqual(
                        store.path,
                        runtime_home / "brain6_artifacts" / "evidence" / "evidence.db",
                    )
                    self.assertTrue(store.path.is_file())
                finally:
                    store.close()

    def test_explicit_evidence_and_task_store_paths_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence_path = root / "custom-evidence.db"
            task_path = root / "custom-tasks.db"
            with patch.dict(os.environ, {
                "BRAIN_RUNTIME_HOME": str(root / "runtime"),
                "BRAIN_EVIDENCE_DB": str(evidence_path),
                "BRAIN_VIRTUAL_TASK_DB": str(task_path),
            }, clear=True):
                evidence = EvidenceStore()
                tasks = DurableTaskStore()
                try:
                    self.assertEqual(evidence.path, evidence_path)
                    self.assertEqual(tasks.path, task_path)
                finally:
                    evidence.close()
                    tasks.close()


if __name__ == "__main__":
    unittest.main()
