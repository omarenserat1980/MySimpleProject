import tempfile
import unittest
from brain_v12.brain.brain_supervisor import BrainSupervisor

class RetestEvidenceIsolationTests(unittest.TestCase):
    def test_previous_attempt_cannot_prove_current_attempt(self):
        s=BrainSupervisor(root=tempfile.mkdtemp(prefix="brain-retest-"),max_cycles=3)
        job=s.create("retest-isolation")
        for phase in ("discover","plan","select_backend","execute"):
            job=s.transition(job,phase,enforce_authority=False)
        s.observe(job["job_id"],"runtime_ok",True,source="attempt-1")
        mission=s.missions[job["job_id"]]
        first_attempt=mission.attempts
        job=s.transition(job,"verify",enforce_authority=False)
        job=s.transition(job,"repair",enforce_authority=False)
        job=s.transition(job,"recover",enforce_authority=False)
        job=s.transition(job,"retry",enforce_authority=False)
        second_attempt=mission.attempts
        self.assertGreater(second_attempt,first_attempt)
        old=s.verification.verify(job["job_id"],required_kind="runtime_ok",mission_id=job["job_id"],attempt=first_attempt)
        current=s.verification.verify(job["job_id"],required_kind="runtime_ok",mission_id=job["job_id"],attempt=second_attempt)
        self.assertTrue(old.verified)
        self.assertFalse(current.verified)

if __name__=="__main__":
    unittest.main()
