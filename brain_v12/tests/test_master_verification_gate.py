import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.execution_verifier import ExecutionVerifier
from brain_v12.brain.master_verification_gate import MasterVerificationGate


class MasterVerificationGateTests(unittest.TestCase):
    def test_verified_completed_requires_real_evidence(self):
        verifier = ExecutionVerifier()
        verifier.register("artifact", ExecutionVerifier.verify_file)
        gate = MasterVerificationGate(verifier)

        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "result.dat"
            p.write_bytes(b"verified")
            out = gate.evaluate("artifact", "local-executor", str(p))

        self.assertEqual(out.status, "VERIFIED_COMPLETED")
        self.assertTrue(out.verified)
        self.assertIn("SHA256_COMPUTED", out.evidence["checks"])

    def test_rejected_evidence_cannot_complete(self):
        verifier = ExecutionVerifier()
        verifier.register("artifact", ExecutionVerifier.verify_file)
        gate = MasterVerificationGate(verifier)
        out = gate.evaluate("artifact", "local-executor", "/missing/result.dat")
        self.assertEqual(out.status, "FAILED")
        self.assertFalse(out.verified)

    def test_no_executor_cannot_complete(self):
        out = MasterVerificationGate().evaluate("artifact", None, "anything")
        self.assertEqual(out.status, "FAILED")
        self.assertEqual(out.reason, "NO_EXECUTOR")


if __name__ == "__main__":
    unittest.main()
