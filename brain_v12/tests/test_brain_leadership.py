import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.brain_identity import IDENTITY_SCHEMA
from brain_v12.brain.brain_leadership import BrainLeadershipStore

def identity(generation=2):
    return {"schema": IDENTITY_SCHEMA, "brain_id": "brain-primary", "generation": generation,
            "source_commit": "a" * 40, "checkpoint_id": "BRAIN-GOLDEN-01"}

def checkpoint():
    return {"checkpoint_id": "BRAIN-GOLDEN-01", "source_commit": "a" * 40, "status": "STABLE_BASELINE"}

class BrainLeadershipTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = BrainLeadershipStore(Path(self.tmp.name) / "leadership.db")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_first_acquisition_and_current(self):
        lease = self.store.acquire(identity(), checkpoint(), "runtime-a", now=100)
        self.assertEqual(lease.fencing_token, 1)
        self.assertTrue(self.store.assert_current(lease, now=101)["verified"])

    def test_second_live_leader_is_blocked(self):
        self.store.acquire(identity(), checkpoint(), "runtime-a", now=100)
        with self.assertRaisesRegex(RuntimeError, "BRAIN_LEADERSHIP_HELD"):
            self.store.acquire(identity(), checkpoint(), "runtime-b", now=101)

    def test_expiry_replaces_leader_and_fences_old_one(self):
        old = self.store.acquire(identity(2), checkpoint(), "runtime-a", now=100, lease_seconds=10)
        new = self.store.acquire(identity(3), checkpoint(), "runtime-b", now=111)
        self.assertEqual(new.fencing_token, 2)
        with self.assertRaisesRegex(RuntimeError, "BRAIN_LEADERSHIP_FENCED"):
            self.store.assert_current(old, now=112)
        self.assertTrue(self.store.assert_current(new, now=112)["verified"])

    def test_stale_holder_cannot_renew(self):
        old = self.store.acquire(identity(), checkpoint(), "runtime-a", now=100, lease_seconds=10)
        self.store.acquire(identity(3), checkpoint(), "runtime-b", now=111)
        with self.assertRaisesRegex(RuntimeError, "BRAIN_LEADERSHIP_RENEW_REJECTED"):
            self.store.renew(old, now=112)

    def test_wrong_checkpoint_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "BRAIN_IDENTITY_CHECKPOINT_MISMATCH"):
            self.store.acquire(identity(), checkpoint() | {"checkpoint_id": "OTHER"}, "runtime-a", now=100)

    def test_release_requires_current_holder(self):
        lease = self.store.acquire(identity(), checkpoint(), "runtime-a", now=100)
        forged = type(lease)(lease.brain_id, lease.generation, lease.lease_id,
                             lease.fencing_token, "runtime-b", lease.acquired_at, lease.expires_at)
        self.assertFalse(self.store.release(forged))
        self.assertTrue(self.store.assert_current(lease, now=101)["verified"])

    def test_execution_contract_requires_current_fencing(self):
        lease = self.store.acquire(identity(), checkpoint(), "runtime-a", now=100)
        self.assertTrue(self.store.assert_contract_fenced(
            {"leadership_fencing_token": lease.fencing_token}, now=101)["verified"])
        with self.assertRaisesRegex(RuntimeError, "BRAIN_LEADERSHIP_FENCED"):
            self.store.assert_contract_fenced({"leadership_fencing_token": lease.fencing_token - 1}, now=101)

    def test_missing_fencing_is_fail_closed(self):
        self.store.acquire(identity(), checkpoint(), "runtime-a", now=100)
        with self.assertRaisesRegex(RuntimeError, "BRAIN_LEADERSHIP_FENCING_REQUIRED"):
            self.store.assert_contract_fenced({}, now=101)

if __name__ == "__main__":
    unittest.main()
