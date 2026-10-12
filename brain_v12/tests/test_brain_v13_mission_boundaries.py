import tempfile
import unittest

from brain_v12.brain.brain_supervisor import BrainSupervisor
from brain_v12.brain.mission import MissionState


class MissionBoundaryTests(unittest.TestCase):
    def test_observation_boundary(self):
        s = BrainSupervisor(root=tempfile.mkdtemp(prefix="brain-v13-observe-"), max_cycles=3)
        job = s.create("observe")
        job = s.transition(job, "discover", enforce_authority=False)
        job = s.transition(job, "plan", enforce_authority=False)
        job = s.transition(job, "select_backend", enforce_authority=False)
        job = s.transition(job, "execute", enforce_authority=False)
        self.assertEqual(s.missions[job["job_id"]].state, MissionState.EXECUTING)
        s.observe(job["job_id"], "runtime_seen", True, source="test")
        self.assertEqual(s.missions[job["job_id"]].state, MissionState.OBSERVING)
        job = s.transition(job, "verify", enforce_authority=False)
        self.assertEqual(s.missions[job["job_id"]].state, MissionState.VERIFYING)

    def test_recovery_boundary(self):
        s = BrainSupervisor(root=tempfile.mkdtemp(prefix="brain-v13-recovery-"), max_cycles=3)
        job = s.create("recover")
        for phase in ("discover", "plan", "select_backend", "execute"):
            job = s.transition(job, phase, enforce_authority=False)
        s.observe(job["job_id"], "runtime_seen", False, source="test")
        job = s.transition(job, "verify", enforce_authority=False)
        job = s.transition(job, "repair", enforce_authority=False)
        self.assertEqual(s.missions[job["job_id"]].state, MissionState.DIAGNOSING)
        job = s.transition(job, "recover", enforce_authority=False)
        self.assertEqual(s.missions[job["job_id"]].state, MissionState.RECOVERING)
        job = s.transition(job, "retry", enforce_authority=False)
        self.assertEqual(s.missions[job["job_id"]].state, MissionState.RETEST)


if __name__ == "__main__":
    unittest.main()
