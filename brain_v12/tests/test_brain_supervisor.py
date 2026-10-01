import tempfile, unittest
from pathlib import Path
from brain_v12.brain.brain_supervisor import BrainSupervisor

class SupervisorTests(unittest.TestCase):
    def test_repair_and_retry_are_bounded(self):
        with tempfile.TemporaryDirectory() as d:
            s=BrainSupervisor(root=d,max_cycles=3)
            job=s.run_simulation("film",verification_ok=False)
            self.assertEqual(job["status"],"completed")
            events=Path(d,"events.jsonl").read_text(encoding="utf-8")
            self.assertIn('"repair"',events)
            self.assertIn('"retry"',events)

    def test_next_action_uses_verification_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            s=BrainSupervisor(root=d,max_cycles=2)
            job=s.create("film")
            self.assertEqual(s.next_action(job, {"ok": True})["action"], "deliver")
            self.assertEqual(s.next_action(job, {"ok": False})["action"], "retry_backend")

    def test_external_actions_require_gate(self):
        with tempfile.TemporaryDirectory() as d:
            s=BrainSupervisor(root=d)
            self.assertFalse(s.authorize_external("move_money")["allowed"])
            self.assertTrue(s.authorize_external("move_money",approved=True)["allowed"])

if __name__ == "__main__":
    unittest.main()
