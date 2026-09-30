import tempfile,unittest
from brain_v12.brain.autonomy_control_plane import ControlPlane

class ControlPlaneTests(unittest.TestCase):
    def test_checkpoint_resume(self):
        with tempfile.TemporaryDirectory() as d:
            cp=ControlPlane(d)
            j=cp.create("film",["plan","render","verify"],max_attempts=3,budget=5)
            j=cp.start_attempt(j)
            j=cp.checkpoint(j,1,{"ok":True})
            self.assertEqual(j["step_index"],1)
            self.assertEqual(j["status"],"ready")

    def test_external_actions_are_gated(self):
        with tempfile.TemporaryDirectory() as d:
            cp=ControlPlane(d)
            j=cp.create("publish",["publish"])
            self.assertEqual(cp.can_run(j,external=True),(False,"external_action_requires_policy_gate"))

if __name__=="__main__": unittest.main()
