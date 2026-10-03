import unittest

from brain_v12.brain.autonomous_supervisor import BrainAutonomousSupervisor
from brain_v12.brain.brain_ai import BrainAI


class Provider:
    def status(self): return {"provider": "test"}
    def respond(self, *args, **kwargs): return {"ok": True, "reply": "ok", "response_id": "r"}


class TestAutonomousSupervisor(unittest.TestCase):
    def test_verified_run_requires_every_step_to_verify(self):
        brain = BrainAI(Provider())
        brain.register_tool("ok", "test", lambda p: {"ok": True, "status": "COMPLETED"})
        result = BrainAutonomousSupervisor(brain).run([{"tool": "ok"}])
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "VERIFIED_COMPLETED")

    def test_high_risk_step_stops_for_approval(self):
        brain = BrainAI(Provider())
        brain.register_tool("write", "test", lambda p: {"ok": True}, risk="high")
        result = BrainAutonomousSupervisor(brain).run([{"tool": "write"}])
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "AUTONOMOUS_RUN_INCOMPLETE")
        self.assertEqual(result["steps"][0]["status"], "WAITING_APPROVAL")

    def test_invalid_plan_never_reports_success(self):
        brain = BrainAI(Provider())
        result = BrainAutonomousSupervisor(brain).run([{}])
        self.assertFalse(result["ok"])
        self.assertNotEqual(result["status"], "VERIFIED_COMPLETED")


if __name__ == "__main__":
    unittest.main()
