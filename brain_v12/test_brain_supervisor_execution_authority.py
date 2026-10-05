import unittest
from brain_v12.brain.brain_supervisor import BrainSupervisor


class FakeGateway:
    def __init__(self, allowed=True):
        self.allowed = allowed

    def authorize(self, capability):
        if not self.allowed:
            raise RuntimeError("BRAIN_INTERNAL_RUNNER_NOT_VERIFIED")
        return type("Decision", (), {"executor": "brain-internal", "verified": True})()


class SupervisorExecutionAuthorityTests(unittest.TestCase):
    def test_execute_phase_requires_internal_authority(self):
        s = BrainSupervisor(execution_gateway=FakeGateway(False))
        job = s.create("authority-test")
        with self.assertRaisesRegex(RuntimeError, "BRAIN_INTERNAL_RUNNER_NOT_VERIFIED"):
            s.transition(job, "execute")

    def test_execute_phase_accepts_verified_internal_authority(self):
        s = BrainSupervisor(execution_gateway=FakeGateway(True))
        job = s.create("authority-test")
        result = s.transition(job, "execute")
        self.assertEqual(result["phase"], "execute")


if __name__ == "__main__":
    unittest.main()
