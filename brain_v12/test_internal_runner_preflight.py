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

    def test_software_preflight_does_not_require_qemu_tools(self):
        with patch.dict(os.environ, {"BRAIN_INTERNAL_RUNNER_FLAG": "1"}, clear=True), \
             patch("brain_v12.brain.internal_runner_preflight.platform.system", return_value="Linux"), \
             patch("brain_v12.brain.internal_runner_preflight.platform.machine", return_value="x86_64"), \
             patch("brain_v12.brain.internal_runner_preflight.which", return_value=None):
            r = inspect_runner("software-test", capability="brain-internal-execution")
            self.assertTrue(r.verified)
            self.assertEqual(r.binaries, {})

    def test_qemu_preflight_still_requires_qemu_tools(self):
        with patch.dict(os.environ, {"BRAIN_INTERNAL_RUNNER_FLAG": "1"}, clear=True), \
             patch("brain_v12.brain.internal_runner_preflight.platform.system", return_value="Linux"), \
             patch("brain_v12.brain.internal_runner_preflight.platform.machine", return_value="x86_64"), \
             patch("brain_v12.brain.internal_runner_preflight.which", return_value=None):
            r = inspect_runner("qemu-test", capability="qemu")
            self.assertFalse(r.verified)
            self.assertIn("REQUIRED_TOOL_MISSING", r.reasons)


if __name__ == "__main__":
    unittest.main()
