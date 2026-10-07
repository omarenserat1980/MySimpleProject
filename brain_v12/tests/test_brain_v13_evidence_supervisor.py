import unittest
from brain_v12.brain.brain_supervisor import BrainSupervisor

class EvidenceSupervisorTests(unittest.TestCase):
    def test_observation_creates_runtime_evidence(self):
        s=BrainSupervisor(root="/tmp/brain-v13-evidence-test")
        job=s.create("evidence")
        s.observe(job["job_id"],"settings_opened",True,source="android-executor")
        result=s.verify_evidence(job["job_id"],required_kind="settings_opened")
        self.assertTrue(result.verified)
        self.assertTrue(result.evidence_ids)

    def test_ci_evidence_does_not_verify_runtime(self):
        s=BrainSupervisor(root="/tmp/brain-v13-ci-test")
        job=s.create("ci-only")
        s.evidence.append(job["job_id"],"ci",{"passed":True},producer="github-actions")
        result=s.verify_evidence(job["job_id"])
        self.assertFalse(result.verified)
        self.assertIn("RUNTIME_EVIDENCE_MISSING",result.reasons)

if __name__=="__main__": unittest.main()
