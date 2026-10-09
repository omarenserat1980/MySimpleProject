import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.iso_download_store import DownloadError, DownloadStore, TRANSITIONS


class IsoDownloadStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = DownloadStore(self.tmp.name, persistent=True)
        self.task = self.store.create(
            owner_id="alice", source="https://downloads.example.test/file.iso",
            expected_size=3, request_id="req-create")

    def tearDown(self):
        self.tmp.cleanup()

    def test_transition_table_has_no_edges_out_of_expired(self):
        self.assertEqual(TRANSITIONS["EXPIRED"], set())
        self.assertEqual(TRANSITIONS["COMPLETED"], {"EXPIRED"})
        self.assertEqual(TRANSITIONS["CANCELLED"], {"EXPIRED"})

    def test_valid_transitions_are_logged_transactionally(self):
        self.store.transition(self.task["download_id"], owner_id="alice",
                              new_state="VALIDATING", reason="validate", request_id="r1")
        self.store.transition(self.task["download_id"], owner_id="alice",
                              new_state="QUEUED", reason="validated", request_id="r2")
        history = self.store.transition_history(self.task["download_id"], owner_id="alice")
        self.assertEqual([x["new_state"] for x in history],
                         ["CREATED", "VALIDATING", "QUEUED"])
        self.assertEqual(history[-1]["request_id"], "r2")

    def test_invalid_transition_does_not_change_state_or_history(self):
        before = self.store.transition_history(self.task["download_id"], owner_id="alice")
        with self.assertRaisesRegex(DownloadError, "INVALID_STATE_TRANSITION"):
            self.store.transition(self.task["download_id"], owner_id="alice",
                                  new_state="COMPLETED", reason="skip validation")
        self.assertEqual(self.store.get(self.task["download_id"], owner_id="alice")["state"], "CREATED")
        self.assertEqual(self.store.transition_history(self.task["download_id"], owner_id="alice"), before)

    def test_terminal_state_cannot_return_to_active_state(self):
        task_id = self.task["download_id"]
        for state in ("VALIDATING", "QUEUED", "CONNECTING", "DOWNLOADING", "VERIFYING", "COMPLETED"):
            self.store.transition(task_id, owner_id="alice", new_state=state, reason="test")
        with self.assertRaisesRegex(DownloadError, "INVALID_STATE_TRANSITION"):
            self.store.transition(task_id, owner_id="alice", new_state="QUEUED", reason="resurrect")

    def test_idempotent_duplicate_transition_has_no_duplicate_event(self):
        task_id = self.task["download_id"]
        self.store.transition(task_id, owner_id="alice", new_state="VALIDATING", reason="start")
        before = len(self.store.transition_history(task_id, owner_id="alice"))
        self.store.transition(task_id, owner_id="alice", new_state="VALIDATING",
                              reason="duplicate", idempotent=True)
        self.assertEqual(len(self.store.transition_history(task_id, owner_id="alice")), before)

    def test_owner_scope_hides_other_users_task(self):
        with self.assertRaisesRegex(DownloadError, "TASK_NOT_FOUND"):
            self.store.get(self.task["download_id"], owner_id="mallory")

    def test_only_one_worker_lease_per_task(self):
        task_id = self.task["download_id"]
        self.assertTrue(self.store.acquire_worker(task_id, worker_id="worker-a"))
        self.assertFalse(self.store.acquire_worker(task_id, worker_id="worker-b"))
        self.assertFalse(self.store.release_worker(task_id, worker_id="worker-b"))
        self.assertTrue(self.store.release_worker(task_id, worker_id="worker-a"))
        self.assertTrue(self.store.acquire_worker(task_id, worker_id="worker-b"))

    def test_expired_worker_lease_can_be_reclaimed_after_crash(self):
        task_id = self.task["download_id"]
        store = DownloadStore(Path(self.tmp.name) / "lease-ttl", persistent=True,
                              lease_ttl_seconds=5)
        task = store.create(owner_id="alice", source="https://downloads.example.test/file.iso")
        task_id = task["download_id"]
        self.assertTrue(store.acquire_worker(task_id, worker_id="worker-crashed"))
        with store._db() as db:
            db.execute("UPDATE worker_leases SET acquired_at=0 WHERE download_id=?", (task_id,))
        self.assertTrue(store.acquire_worker(task_id, worker_id="worker-recovery"))
        self.assertFalse(store.renew_worker(task_id, worker_id="worker-crashed"))
        self.assertTrue(store.renew_worker(task_id, worker_id="worker-recovery"))

    def test_active_worker_lease_cannot_be_stolen_and_wrong_worker_cannot_renew(self):
        task_id = self.task["download_id"]
        self.assertTrue(self.store.acquire_worker(task_id, worker_id="worker-a"))
        self.assertFalse(self.store.acquire_worker(task_id, worker_id="worker-b"))
        self.assertFalse(self.store.renew_worker(task_id, worker_id="worker-b"))
        self.assertTrue(self.store.renew_worker(task_id, worker_id="worker-a"))

    def test_fencing_token_invalidates_worker_after_lease_recovery(self):
        task_id = self.task["download_id"]
        first = self.store.acquire_worker_token(task_id, worker_id="worker-a")
        self.assertIsInstance(first, int)
        self.assertTrue(self.store.assert_worker_lease(
            task_id, worker_id="worker-a", generation=first))
        with self.store._db() as db:
            db.execute("UPDATE worker_leases SET acquired_at=0 WHERE download_id=?", (task_id,))
        second = self.store.acquire_worker_token(task_id, worker_id="worker-b")
        self.assertGreater(second, first)
        self.assertFalse(self.store.assert_worker_lease(
            task_id, worker_id="worker-a", generation=first))
        self.assertFalse(self.store.renew_worker_lease(
            task_id, worker_id="worker-a", generation=first))
        self.assertTrue(self.store.renew_worker_lease(
            task_id, worker_id="worker-b", generation=second))

    def test_existing_worker_lease_schema_is_migrated(self):
        root = Path(self.tmp.name) / "legacy-db"
        legacy = DownloadStore(root, persistent=True)
        with legacy._db() as db:
            db.execute("ALTER TABLE downloads DROP COLUMN lease_generation")
            db.execute("ALTER TABLE worker_leases DROP COLUMN generation")
        migrated = DownloadStore(root, persistent=True)
        task = migrated.create(owner_id="bob", source="https://downloads.example.test/a.iso")
        token = migrated.acquire_worker_token(task["download_id"], worker_id="migrated-worker")
        self.assertEqual(token, 1)

    def test_invalid_lease_ttl_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "lease_ttl_seconds"):
            DownloadStore(Path(self.tmp.name) / "invalid-ttl", persistent=True,
                          lease_ttl_seconds=0)

    def test_resumable_task_requires_declared_persistent_storage(self):
        ephemeral = DownloadStore(Path(self.tmp.name) / "ephemeral", persistent=False)
        with self.assertRaisesRegex(DownloadError, "PERSISTENT_STORAGE_REQUIRED"):
            ephemeral.create(owner_id="alice", source="https://example.test/a.iso", resumable=True)
        task = ephemeral.create(owner_id="alice", source="https://example.test/a.iso", resumable=False)
        self.assertEqual(task["state"], "CREATED")

    def test_server_paths_are_owned_and_reject_traversal(self):
        path = self.store.server_path(self.task["download_id"], area="partial")
        self.assertEqual(path.parent, self.store.partial.resolve())
        with self.assertRaisesRegex(DownloadError, "INVALID_REQUEST"):
            self.store.server_path("../outside", area="partial")
        with self.assertRaisesRegex(DownloadError, "INVALID_REQUEST"):
            self.store.server_path(self.task["download_id"], area="../../tmp")

    def test_server_path_rejects_symlink_even_when_target_stays_inside_root(self):
        task_id = self.task["download_id"]
        original = self.store.partial / f"{task_id}.part"
        linked_target = self.store.partial / "other-task.part"
        linked_target.write_bytes(b"fixture")
        try:
            original.symlink_to(linked_target)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable on this platform")
        with self.assertRaisesRegex(DownloadError, "INVALID_STORAGE_PATH"):
            self.store.server_path(task_id, area="partial")

    def test_cleanup_result_is_explicit_and_owned(self):
        self.store.record_cleanup(self.task["download_id"], owner_id="alice",
                                  result="CLEANUP_FAILED", reason="permission denied")
        row = self.store.get(self.task["download_id"], owner_id="alice")
        self.assertEqual(row["cleanup_result"], "CLEANUP_FAILED")
        with self.assertRaisesRegex(DownloadError, "TASK_NOT_FOUND"):
            self.store.record_cleanup(self.task["download_id"], owner_id="mallory",
                                      result="CLEANED", reason="wrong owner")


if __name__ == "__main__":
    unittest.main()
