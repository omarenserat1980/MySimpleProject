import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.execution_verifier import ExecutionVerifier


class ArtifactVerificationTests(unittest.TestCase):
    def test_real_artifact_is_verified(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "output.bin"
            p.write_bytes(b"real output")
            result = ExecutionVerifier.verify_file(str(p))
            self.assertTrue(result["verified"])
            self.assertIn("ARTIFACT_EXISTS", result["checks"])
            self.assertEqual(result["bytes"], 11)
            self.assertEqual(len(result["sha256"]), 64)

    def test_missing_artifact_is_rejected(self):
        result = ExecutionVerifier.verify_file("/definitely/missing/brain-artifact.bin")
        self.assertFalse(result["verified"])
        self.assertEqual(result["checks"], ["ARTIFACT_MISSING"])

    def test_empty_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "empty.bin"
            p.touch()
            result = ExecutionVerifier.verify_file(str(p))
            self.assertFalse(result["verified"])
            self.assertEqual(result["checks"], ["ARTIFACT_EMPTY"])


if __name__ == "__main__":
    unittest.main()
