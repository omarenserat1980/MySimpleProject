import unittest

from brain_v12.brain.execution_verifier import ExecutionVerifier


class ExecutionVerifierTests(unittest.TestCase):
    def test_missing_verifier_is_not_success(self):
        evidence = ExecutionVerifier().verify("media.render", "ffmpeg", "output.mp4")
        self.assertFalse(evidence.verified)
        self.assertEqual(evidence.checks, ("NO_VERIFIER_REGISTERED",))

    def test_verifier_accepts_result(self):
        verifier = ExecutionVerifier()
        verifier.register("text", lambda value: {"verified": value == "ok", "checks": ["MATCH"]})
        evidence = verifier.verify("text", "executor", "ok")
        self.assertTrue(evidence.verified)
        self.assertEqual(evidence.checks, ("MATCH",))

    def test_verifier_exception_is_failure(self):
        verifier = ExecutionVerifier()
        verifier.register("x", lambda _: 1 / 0)
        evidence = verifier.verify("x", "executor", "value")
        self.assertFalse(evidence.verified)
        self.assertEqual(evidence.checks, ("VERIFIER_ERROR",))


if __name__ == "__main__":
    unittest.main()
