import os
import unittest
from unittest.mock import patch

from brain_v12.brain.internal_runner import InternalRunner


class InternalRunnerTruthTests(unittest.TestCase):
    def test_runner_defaults_offline(self):
        r = InternalRunner()
        self.assertEqual(r.state, "OFFLINE")

    def test_status_cannot_claim_online_without_verified_preflight(self):
        with patch.dict(os.environ, {"BRAIN_INTERNAL_RUNNER_FLAG": "0"}, clear=False):
            status = InternalRunner().status()
        self.assertEqual(status["state"], "OFFLINE")
        self.assertFalse(status["preflight"]["verified"])

    def test_require_rejects_unverified_host(self):
        with patch.dict(os.environ, {"BRAIN_INTERNAL_RUNNER_FLAG": "0"}, clear=False):
            with self.assertRaisesRegex(RuntimeError, "BRAIN_INTERNAL_RUNNER_NOT_VERIFIED"):
                InternalRunner().require("brain-internal-execution")


if __name__ == "__main__":
    unittest.main()


    def test_direct_run_rejects_unverified_host(self):
        with patch.dict(os.environ, {"BRAIN_INTERNAL_RUNNER_FLAG": "0"}, clear=False):
            with self.assertRaisesRegex(RuntimeError, "BRAIN_INTERNAL_RUNNER_NOT_VERIFIED"):
                InternalRunner().run(["python", "-c", "print('must not run')"])
