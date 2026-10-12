import os
import unittest
from unittest.mock import patch

from brain_v12.brain.internal_runner_preflight import (
    inspect_runner,
    invalidate_preflight_cache,
)


class InternalRunnerPreflightTests(unittest.TestCase):
    def setUp(self):
        invalidate_preflight_cache()

    def tearDown(self):
        invalidate_preflight_cache()

    def _probe(self, *, attested: bool, euid: int):
        with (
            patch.dict(os.environ, {"RUNNER_NAME": "brain-internal-arkan"}, clear=True),
            patch("brain_v12.brain.internal_runner_preflight._host_attestation_valid", return_value=attested),
            patch("brain_v12.brain.internal_runner_preflight.which", return_value="/usr/bin/mock-tool"),
            patch("brain_v12.brain.internal_runner_preflight.platform.system", return_value="Linux"),
            patch("brain_v12.brain.internal_runner_preflight.platform.machine", return_value="x86_64"),
            patch("brain_v12.brain.internal_runner_preflight.os.geteuid", return_value=euid),
        ):
            return inspect_runner()

    def test_not_online_without_host_attestation(self):
        r = self._probe(attested=False, euid=1000)
        self.assertFalse(r.online)
        self.assertIn("HOST_ATTESTATION_MISSING_OR_INVALID", r.reasons)

    def test_online_requires_host_attestation(self):
        r = self._probe(attested=True, euid=1000)
        self.assertTrue(r.online)
        self.assertTrue(r.verified)
        self.assertEqual(r.reasons, ())

    def test_rejects_root_execution_even_with_host_attestation(self):
        r = self._probe(attested=True, euid=0)
        self.assertFalse(r.verified)
        self.assertIn("RUNNER_MUST_NOT_RUN_AS_ROOT", r.reasons)


if __name__ == "__main__":
    unittest.main()
