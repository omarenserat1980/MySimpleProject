import unittest
from brain_v12.brain.sync_engine import BrainSyncStore, SyncConflict

class BrainSyncStoreTests(unittest.TestCase):
    def test_idempotent_put_and_conflict_detection(self):
        s = BrainSyncStore("cloud")
        first = s.put("task/1", {"status": "READY"}, event_id="e1")
        again = s.put("task/1", {"status": "READY"}, event_id="e1")
        self.assertEqual(first, again)
        with self.assertRaises(SyncConflict):
            s.put("task/1", {"status": "RUNNING"}, expected_revision=0, event_id="e2")

    def test_offline_replica_converges_and_old_events_do_not_overwrite(self):
        cloud = BrainSyncStore("cloud")
        phone = BrainSyncStore("redmi3-01")
        e1 = cloud.put("task/1", {"status": "READY"}, event_id="e1")
        phone.apply([e1])
        e2 = cloud.put("task/1", {"status": "DONE"}, expected_revision=1, event_id="e2")
        phone.apply([e2, e1])
        self.assertEqual(phone.get("task/1").value["status"], "DONE")
        self.assertEqual(phone.revision("task/1"), 2)

    def test_tombstone_and_audit_chain(self):
        cloud = BrainSyncStore("cloud")
        phone = BrainSyncStore("redmi3-01")
        e1 = cloud.put("memory/x", {"v": 1}, event_id="e1")
        e2 = cloud.delete("memory/x", expected_revision=1, event_id="e2")
        phone.apply([e1, e2])
        self.assertTrue(phone.get("memory/x").deleted)
        self.assertTrue(cloud.audit_chain_valid())

    def test_snapshot_is_deterministic(self):
        a = BrainSyncStore("a")
        b = BrainSyncStore("b")
        a.put("b", {"n": 2}, event_id="b1")
        a.put("a", {"n": 1}, event_id="a1")
        b.apply(a.export_events())
        self.assertEqual(a.snapshot()["digest"], b.snapshot()["digest"])
