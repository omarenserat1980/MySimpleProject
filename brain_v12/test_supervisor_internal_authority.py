import tempfile
import unittest

from brain_v12.brain.brain_supervisor import BrainSupervisor


class SupervisorAuthorityTests(unittest.TestCase):
    def test_submit_fails_closed_without_internal_authority(self):
        class OfflineGateway:
            def authorize(self, capability):
                raise RuntimeError("BRAIN_INTERNAL_RUNNER_NOT_VERIFIED")

        with tempfile.TemporaryDirectory() as d:
            s = BrainSupervisor(root=d, execution_gateway=OfflineGateway())
            job = s.create("build")
            with self.assertRaisesRegex(RuntimeError, "BRAIN_INTERNAL_RUNNER_NOT_VERIFIED"):
                s.transition(job, "execute")

    def test_submit_records_verified_internal_authority(self):
        class OnlineGateway:
            def authorize(self, capability):
                return type("Decision", (), {
                    "executor": "brain-internal",
                    "verified": True,
                })()

        with tempfile.TemporaryDirectory() as d:
            s = BrainSupervisor(root=d, execution_gateway=OnlineGateway())
            job = s.create("build")
            result = s.transition(job, "execute")
            self.assertEqual(result["phase"], "execute")


if __name__ == "__main__":
    unittest.main()
