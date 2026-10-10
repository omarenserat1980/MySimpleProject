from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from brain_v12.brain import cloud_executor_gate


class CloudExecutorGateModeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = {
            "BRAIN_CLOUD_EXECUTOR": "1",
            "BRAIN_CLOUD_EXECUTOR_ID": "test-executor",
            "BRAIN_CLOUD_EXECUTOR_ATTESTATION": "test-attestation",
        }
        self.patches = [
            patch.dict(os.environ, self.env, clear=False),
            patch.object(cloud_executor_gate.platform, "machine", return_value="x86_64"),
            patch.object(cloud_executor_gate.shutil, "which", side_effect=lambda name: "/usr/bin/" + name),
            patch.object(cloud_executor_gate, "_run", side_effect=self.fake_run),
            patch.object(cloud_executor_gate, "_probe_accelerator", return_value=(True, "probe-ok")),
            patch.object(cloud_executor_gate.socket, "gethostname", return_value="test-host"),
            patch.object(cloud_executor_gate.os, "access", return_value=True),
            patch.object(cloud_executor_gate.Path, "exists", return_value=True),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self) -> None:
        for item in reversed(self.patches):
            item.stop()

    @staticmethod
    def fake_run(cmd, timeout=10):
        if cmd[-1] == "--version":
            return True, "QEMU emulator version test"
        if cmd[-2:] == ["-accel", "help"]:
            return True, "kvm tcg"
        return True, "ok"

    def test_kvm_remains_production_verified(self) -> None:
        os.environ["BRAIN_EXECUTOR_ACCELERATOR"] = "kvm"
        result = cloud_executor_gate.check("/tmp/brain-kvm-gate-test.json")
        self.assertTrue(result["verified"])
        self.assertFalse(result["diagnostic_verified"])
        self.assertEqual(result["production_capability"], "KVM")

    def test_tcg_is_diagnostic_only(self) -> None:
        os.environ["BRAIN_EXECUTOR_ACCELERATOR"] = "tcg-diagnostic"
        result = cloud_executor_gate.check("/tmp/brain-tcg-gate-test.json")
        self.assertFalse(result["verified"])
        self.assertTrue(result["diagnostic_verified"])
        self.assertEqual(result["production_capability"], "TCG-DIAGNOSTIC-ONLY")

    def test_unknown_mode_is_blocked(self) -> None:
        os.environ["BRAIN_EXECUTOR_ACCELERATOR"] = "unknown"
        result = cloud_executor_gate.check("/tmp/brain-invalid-gate-test.json")
        self.assertFalse(result["verified"])
        self.assertFalse(result["diagnostic_verified"])
        self.assertFalse(result["checks"]["accelerator_mode"]["ok"])


if __name__ == "__main__":
    unittest.main()
