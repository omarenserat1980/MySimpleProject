import tempfile, time, unittest
from pathlib import Path
from brain_v12.brain.durable_task_store import DurableTaskStore

class DurableTaskRecoveryTests(unittest.TestCase):
    def test_spec_survives_finish_and_result_is_separate(self):
        with tempfile.TemporaryDirectory() as d:
            s=DurableTaskStore(Path(d)/"tasks.db")
            s.submit("t1",{"program":[["HALT"]],"required_capabilities":["cpu"],"requirement":{}})
            row=s.claim("t1","blade-1",30); self.assertEqual(row["attempt"],1)
            finished=s.finish("t1",row["lease_id"],True,{"ok":True,"stdout":"done"})
            self.assertEqual(finished["status"],"COMPLETED")
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

if __name__=="__main__": unittest.main()
