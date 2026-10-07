import tempfile
import unittest
from brain_v12.brain.brain_supervisor import BrainSupervisor
from brain_v12.brain.mission import MissionState

class MissionSupervisorIntegrationTests(unittest.TestCase):
    def test_supervisor_phases_update_mission(self):
        s=BrainSupervisor(root=tempfile.mkdtemp(prefix="brain-v13-mission-"), max_cycles=3)
        job=s.create("mission")
        expected={"discover":"UNDERSTANDING","plan":"PLANNING","select_backend":"READY","execute":"EXECUTING","verify":"VERIFYING"}
        for phase,state in expected.items():
            job=s.transition(job,phase,enforce_authority=False)
            self.assertEqual(s.missions[job["job_id"]].state, MissionState[state])
        s.observe(job["job_id"],"runtime_ok",True,source="test")
        job=s.transition(job,"deliver",status="completed",required_evidence_kind="runtime_ok",enforce_authority=False)
        self.assertEqual(s.missions[job["job_id"]].state,MissionState.COMPLETED)

if __name__=="__main__": unittest.main()
