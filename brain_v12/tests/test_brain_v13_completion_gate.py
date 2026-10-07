import tempfile
import unittest
from brain_v12.brain.brain_supervisor import BrainSupervisor

class CompletionEvidenceGateTests(unittest.TestCase):
    def make(self):
        return BrainSupervisor(root=tempfile.mkdtemp(prefix="brain-v13-gate-"))

    def test_deliver_without_runtime_evidence_is_blocked(self):
        s=self.make(); job=s.create("no evidence")
        out=s.transition(job,"deliver",status="completed",details={"claimed":True})
        self.assertEqual(out["status"],"blocked")

    def test_ci_only_evidence_cannot_complete(self):
        s=self.make(); job=s.create("ci only")
        s.evidence.append(job["job_id"],"ci",{"passed":True},producer="github-actions")
        out=s.transition(job,"deliver",status="completed")
        self.assertEqual(out["status"],"blocked")

    def test_runtime_evidence_allows_completion(self):
        s=self.make(); job=s.create("runtime")
        s.observe(job["job_id"],"settings_opened",True,source="android-executor")
        out=s.transition(job,"deliver",status="completed",required_evidence_kind="settings_opened")
        self.assertEqual(out["status"],"completed")

    def test_required_kind_is_enforced(self):
        s=self.make(); job=s.create("wrong kind")
        s.observe(job["job_id"],"other_runtime",True,source="android-executor")
        out=s.transition(job,"deliver",status="completed",required_evidence_kind="settings_opened")
        self.assertEqual(out["status"],"blocked")

    def test_tampered_evidence_cannot_complete(self):
        s=self.make(); job=s.create("tampered")
        item=s.evidence.append(job["job_id"],"settings_opened",{"value":True},producer="android-executor")
        s.evidence.db.execute("UPDATE evidence SET payload=? WHERE evidence_id=?",( '{"value":false}', item["evidence_id"]))
        s.evidence.db.commit()
        out=s.transition(job,"deliver",status="completed",required_evidence_kind="settings_opened")
        self.assertEqual(out["status"],"blocked")

if __name__=="__main__":
    unittest.main()
