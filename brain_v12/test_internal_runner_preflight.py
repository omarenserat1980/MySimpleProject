import os
import unittest
from unittest.mock import patch

from brain_v12.brain.internal_runner_preflight import inspect_runner


class InternalRunnerPreflightTests(unittest.TestCase):
    def test_not_online_without_runtime_flag(self):
        with patch.dict(os.environ, {}, clear=True):
            r = inspect_runner()
            self.assertFalse(r.online)
            self.assertIn("INTERNAL_RUNNER_FLAG_MISSING", r.reasons)

    def test_online_claim_requires_runtime_flag(self):
        with patch.dict(os.environ, {"BRAIN_INTERNAL_RUNNER_FLAG": "1"}, clear=True):
            r = inspect_runner()
            self.assertTrue(r.online)


if __name__ == "__main__":
    unittest.main()
