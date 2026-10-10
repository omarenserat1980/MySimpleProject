import os
import unittest
from unittest.mock import patch

from brain_v12.brain.internal_runner_preflight import inspect_runner


class InternalRunnerPreflightTests(unittest.TestCase):
    def test_not_online_without_host_attestation(self):
        with (
            patch.dict(os.environ, {"RUNNER_NAME": "brain-internal-arkan"}, clear=True),
            patch("brain_v12.brain.internal_runner_preflight._host_attestation_valid", return_value=False),
            patch("brain_v12.brain.internal_runner_preflight.which", return_value="/usr/bin/mock-tool"),
            patch("brain_v12.brain.internal_runner_preflight.platform.system", return_value="Linux"),
            patch("brain_v12.brain.internal_runner_preflight.platform.machine", return_value="x86_64"),
            patch("brain_v12.brain.internal_runner_preflight.os.geteuid", return_value=1000),
        ):
            r = inspect_runner()
            self.assertFalse(r.online)
            self.assertIn("HOST_ATTESTATION_MISSING_OR_INVALID", r.reasons)

    def test_online_requires_host_attestation(self):
        with (
            patch.dict(os.environ, {"RUNNER_NAME": "brain-internal-arkan"}, clear=True),
            patch("brain_v12.brain.internal_runner_preflight._host_attestation_valid", return_value=True),
            patch("brain_v12.brain.internal_runner_preflight.which", return_value="/usr/bin/mock-tool"),
            patch("brain_v12.brain.internal_runner_preflight.platform.system", return_value="Linux"),
            patch("brain_v12.brain.internal_runner_preflight.platform.machine", return_value="x86_64"),
            patch("brain_v12.brain.internal_runner_preflight.os.geteuid", return_value=1000),
        ):
            r = inspect_runner()
            self.assertTrue(r.online)
            self.assertTrue(r.verified)
            self.assertEqual(r.reasons, ())


if __name__ == "__main__":
    unittest.main()
