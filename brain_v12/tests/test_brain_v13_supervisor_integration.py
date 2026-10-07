import unittest
from brain_v12.brain.brain_supervisor import BrainSupervisor

class SupervisorV13IntegrationTests(unittest.TestCase):
    def test_v13_layers_are_attached_to_single_supervisor(self):
        s=BrainSupervisor(root="/tmp/brain-v13-test")
        self.assertEqual(s.constitution.check()["orchestrator_authority"],"single")
        job=s.create("integration")
        self.assertIn(job["job_id"],s.missions)
        contract=s.execution_contract(job,"test")
        self.assertEqual(contract.mission_id,job["job_id"])
        obs=s.observe(job["job_id"],"runtime","READY")
        self.assertEqual(obs.value,"READY")
        self.assertEqual(s.reality.resolve("runtime").value,"READY")

if __name__=="__main__": unittest.main()
