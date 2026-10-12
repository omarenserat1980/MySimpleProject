import tempfile
import unittest
from brain_v12.brain.brain_supervisor import BrainSupervisor
from brain_v12.brain.golden_acceptance_gate import AcceptanceCriterion
from brain_v12.brain.mission import MissionState

class MissionSupervisorIntegrationTests(unittest.TestCase):
    def test_supervisor_phases_update_mission(self):
        s=BrainSupervisor(root=tempfile.mkdtemp(prefix="brain-v13-mission-"), max_cycles=3)
        job=s.create("mission")
        expected={"discover":"UNDERSTANDING","plan":"PLANNING","select_backend":"READY","execute":"EXECUTING","observe":"OBSERVING","verify":"VERIFYING"}
        for phase,state in expected.items():
            job=s.transition(job,phase,enforce_authority=False)
            self.assertEqual(s.missions[job["job_id"]].state, MissionState[state])
        s.observe(job["job_id"],"runtime_ok",True,source="test")
        mission=s.missions[job["job_id"]]
        runtime=s.evidence.append(
            job["job_id"],"runtime_ok",
            {"value":True,"reality_level":"SIMULATED"},
            producer="fixture-executor",mission_id=job["job_id"],
            attempt=mission.attempts,phase="VERIFYING",
        )
        s.evidence.append(
            job["job_id"],"independent_verification",
            {"verified":True,"reality_level":"SIMULATED",
             "verified_evidence_ids":[runtime["evidence_id"]],
             "criterion_ids":["runtime-ok"]},
            producer="fixture-verifier",mission_id=job["job_id"],
            attempt=mission.attempts,phase="VERIFYING",
        )
        job=s.deliver_if_golden(
            job,(AcceptanceCriterion("runtime-ok","runtime_ok"),),
            expected_reality="SIMULATED",
        )
        self.assertEqual(job["status"],"completed")
        self.assertEqual(s.missions[job["job_id"]].state,MissionState.COMPLETED)

if __name__=="__main__": unittest.main()
