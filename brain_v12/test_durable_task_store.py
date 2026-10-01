import tempfile, time, unittest
from pathlib import Path
from .brain.durable_task_store import DurableTaskStore

class DurableTaskStoreTests(unittest.TestCase):
    def make(self):
        p=Path(tempfile.mkdtemp())/"tasks.db"
        return DurableTaskStore(p)

    def test_idempotent_submit_and_atomic_claim(self):
        db=self.make()
        a=db.submit("t1",{"program":[["HALT"]]})
        b=db.submit("t1",{"program":[["OTHER"]]})
        self.assertEqual(a["task_id"],b["task_id"])
        c=db.claim("t1","blade-1")
        self.assertEqual(c["status"],"RUNNING")
        self.assertIsNone(db.claim("t1","blade-2"))
        self.assertTrue(db.heartbeat("t1",c["lease_id"]))

    def test_expired_running_task_is_requeued(self):
        db=self.make()
        db.submit("t2",{"x":1})
        c=db.claim("t2","blade-1",lease_seconds=5)
        with db.lock:
            db.db.execute("UPDATE tasks SET lease_expires_at=? WHERE task_id=?", (time.time()-1,"t2"))
            db.db.commit()
        self.assertEqual(db.recover_expired(),1)
        self.assertEqual(db.get("t2")["status"],"QUEUED")

if __name__=="__main__":
    unittest.main()
