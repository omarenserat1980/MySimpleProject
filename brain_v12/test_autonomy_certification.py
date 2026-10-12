import tempfile
import unittest

from brain_v12.brain.autonomy_certification import (
    require_certified,
    run_independence_test,
)
from brain_v12.brain.execution_gateway import BrainExecutionGateway
from brain_v12.brain.internal_task_runtime import InternalTaskRuntime


class FakeRunner:
    def require(self, capability):
        return None

    def run(self, argv, cwd=None, timeout=None):
        class Result:
            returncode = 0
            stdout = "BRAIN_AUTONOMY_PROOF"
            stderr = ""
        return Result()


class AutonomyCertificationTests(unittest.TestCase):
    def test_certification_requires_all_real_contracts(self):
        with tempfile.TemporaryDirectory() as d:
            root = __import__("pathlib").Path(d)

            def runtime_factory(path):
                return InternalTaskRuntime(
                    path, BrainExecutionGateway(FakeRunner())
                )

            evidence = run_independence_test(
                runtime_factory,
                lambda: runtime_factory(root),
                root,
            )
            self.assertEqual(evidence["status"], "AUTONOMOUS_WITHIN_AUTHORITY")
            self.assertTrue(evidence["github_independent"])
            self.assertTrue(evidence["evidence_ref"])
            self.assertTrue(evidence["execution_contract"]["verified"])
            self.assertIn("BRAIN_EXECUTION_FABRIC", evidence["execution_contract"]["contract"])

    def test_uncertified_state_cannot_be_claimed(self):
        with self.assertRaisesRegex(
            RuntimeError, "AUTONOMOUS_WITHIN_AUTHORITY_NOT_PROVEN"
        ):
            require_certified({"status": "INTERNAL_RUNTIME_CODE_PRESENT"})


if __name__ == "__main__":
    unittest.main()
