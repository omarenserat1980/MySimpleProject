import tempfile
import unittest
from brain_v12.brain.brain_supervisor import BrainSupervisor

class EvidenceLineageTests(unittest.TestCase):
    def test_observation_is_bound_to_mission_and_attempt(self):
        s=BrainSupervisor(root=tempfile.mkdtemp(prefix="brain-lineage-"),max_cycles=3)
        job=s.create("lineage")
        for phase in ("discover","plan","select_backend","execute"):
            job=s.transition(job,phase,enforce_authority=False)
        s.observe(job["job_id"],"runtime_ok",True,source="test")
        mission=s.missions[job["job_id"]]
        self.assertEqual(len(mission.evidence_ids),1)
        item=s.evidence.get(mission.evidence_ids[0])
        self.assertEqual(item["mission_id"],job["job_id"])
        self.assertEqual(item["attempt"],mission.attempts)
        result=s.verification.verify(job["job_id"],required_kind="runtime_ok",mission_id=job["job_id"],attempt=mission.attempts)
        self.assertTrue(result.verified)
        other=s.verification.verify(job["job_id"],required_kind="runtime_ok",mission_id="different-mission",attempt=mission.attempts)
        self.assertFalse(other.verified)

if __name__=="__main__":
    unittest.main()
