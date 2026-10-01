import tempfile, unittest
from pathlib import Path
from brain_v12.brain.evidence_store import EvidenceStore
from brain_v12.brain.verification_engine import VerificationEngine

class T:
    task_id="t1"; status="COMPLETED"; attempt=1; result={"ok":True,"value":7}

class EvidenceVerificationTests(unittest.TestCase):
    def test_evidence_hash_and_verification(self):
        with tempfile.TemporaryDirectory() as d:
            store=EvidenceStore(Path(d)/"evidence.db")
            engine=VerificationEngine(store)
            result=engine.verify_execution(T())
            self.assertEqual(result["status"],"VERIFIED")
            item=store.get(result["evidence_id"])
            self.assertEqual(store.verify_hash(item["evidence_id"])["status"],"VERIFIED")
            store.close()

    def test_tamper_is_detected(self):
        with tempfile.TemporaryDirectory() as d:
            store=EvidenceStore(Path(d)/"evidence.db")
            ev=store.append("t1","execution",{"ok":True})
            store.db.execute("UPDATE evidence SET payload=? WHERE evidence_id=?",
                ('{"ok":false}',ev["evidence_id"])); store.db.commit()
            self.assertEqual(store.verify_hash(ev["evidence_id"])["status"],"TAMPERED")
            store.close()

if __name__=="__main__": unittest.main()
