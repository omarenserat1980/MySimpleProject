import tempfile, time, unittest
from pathlib import Path
from brain_v12.brain.durable_task_store import DurableTaskStore

class DurableTaskRecoveryTests(unittest.TestCase):
    def test_spec_survives_finish_and_result_is_separate(self):
        with tempfile.TemporaryDirectory() as d:
            s=DurableTaskStore(Path(d)/"tasks.db")
            s.submit("t1",{"program":[["HALT"]],"required_capabilities":["cpu"],"requirement":{}})
            row=s.claim("t1","blade-1",30); self.assertEqual(row["attempt"],1)
            s.finish("t1",True,{"ok":True,"stdout":"done"},row["lease_id"])
            row=s.get("t1")
            self.assertIn("HALT",row["payload"]); self.assertIn("done",row["result_json"])
            s.close()

    def test_atomic_claim_and_expired_recovery(self):
        with tempfile.TemporaryDirectory() as d:
            s=DurableTaskStore(Path(d)/"tasks.db")
            s.submit("t1",{"program":[],"required_capabilities":["cpu"],"requirement":{}})
            self.assertIsNotNone(s.claim("t1","b1",1)); self.assertIsNone(s.claim("t1","b2",1))
            time.sleep(1.1); ids=s.recover_expired(); self.assertEqual(ids,["t1"])
            self.assertEqual(s.get("t1")["status"],"QUEUED"); s.close()

    def test_stale_lease_cannot_finish_reclaimed_task(self):
        with tempfile.TemporaryDirectory() as d:
            s=DurableTaskStore(Path(d)/"tasks.db")
            s.submit("fenced", {"program": []})
            first=s.claim("fenced", "worker-old", 30)
            with s.lock:
                s.db.execute("UPDATE tasks SET lease_expires_at=? WHERE task_id=?", (time.time()-1, "fenced"))
                s.db.commit()
            self.assertEqual(s.recover_expired(), ["fenced"])
            second=s.claim("fenced", "worker-new", 30)
            self.assertNotEqual(first["lease_id"], second["lease_id"])
            self.assertIsNone(s.finish("fenced", True, {"worker":"old"}, first["lease_id"]))
            current=s.get("fenced")
            self.assertEqual(current["status"], "RUNNING")
            self.assertIsNone(current["result_json"])
            completed=s.finish("fenced", True, {"worker":"new"}, second["lease_id"])
            self.assertEqual(completed["status"], "COMPLETED")
            self.assertIn("new", completed["result_json"])
            s.close()

if __name__=="__main__": unittest.main()
