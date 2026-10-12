import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain_v12.brain.cloud_executor_gate import check


class CloudExecutorGateTests(unittest.TestCase):
    def _patch_substrate(self, *, kvm_exists=True):
        return [
            patch("brain_v12.brain.cloud_executor_gate.platform.machine", return_value="x86_64"),
            patch("brain_v12.brain.cloud_executor_gate.Path.exists", return_value=kvm_exists),
            patch("brain_v12.brain.cloud_executor_gate.os.access", return_value=True),
            patch("brain_v12.brain.cloud_executor_gate.shutil.which", side_effect=lambda x: "/usr/bin/qemu-system-x86_64" if x == "qemu-system-x86_64" else "/usr/bin/python"),
            patch("brain_v12.brain.cloud_executor_gate._run", side_effect=[(True, "QEMU emulator version 9"), (True, "kvm")]),
            patch("brain_v12.brain.cloud_executor_gate._probe_kvm", return_value=(True, "qemu-initialized-kvm-and-paused")),
        ]

    def test_gate_passes_only_with_verified_attestation_and_substrate(self):
        with tempfile.TemporaryDirectory() as td, patch.dict("os.environ", {
            "BRAIN_CLOUD_EXECUTOR": "1", "BRAIN_CLOUD_EXECUTOR_ID": "cloud-test-01"
        }), patch("brain_v12.brain.cloud_executor_gate.verify_from_environment", return_value={
            "verified": True, "expires_at": 1800000300, "audience": "brain-cloud-executor"
        }):
            patches = self._patch_substrate()
            for item in patches: item.start()
            self.addCleanup(lambda: [item.stop() for item in patches])
            out = str(Path(td) / "gate.json")
            evidence = check(out)
            self.assertTrue(evidence["verified"])
            self.assertTrue(json.loads(Path(out).read_text())["verified"])
            self.assertTrue(evidence["checks"]["cloud_executor_attestation"]["ok"])

    def test_gate_fails_when_attestation_rejected(self):
        with tempfile.TemporaryDirectory() as td, patch.dict("os.environ", {
            "BRAIN_CLOUD_EXECUTOR": "1", "BRAIN_CLOUD_EXECUTOR_ID": "cloud-test-01"
        }), patch("brain_v12.brain.cloud_executor_gate.verify_from_environment", side_effect=ValueError("CLOUD_EXECUTOR_ATTESTATION_SIGNATURE_INVALID")):
            patches = self._patch_substrate()
            for item in patches: item.start()
            self.addCleanup(lambda: [item.stop() for item in patches])
            evidence = check(str(Path(td) / "gate.json"))
            self.assertFalse(evidence["verified"])
            self.assertFalse(evidence["checks"]["cloud_executor_attestation"]["ok"])

    def test_gate_fails_without_kvm(self):
        with tempfile.TemporaryDirectory() as td, patch.dict("os.environ", {
            "BRAIN_CLOUD_EXECUTOR": "1", "BRAIN_CLOUD_EXECUTOR_ID": "cloud-test-01"
        }), patch("brain_v12.brain.cloud_executor_gate.verify_from_environment", return_value={
            "verified": True, "expires_at": 1800000300, "audience": "brain-cloud-executor"
        }):
            patches = self._patch_substrate(kvm_exists=False)
            for item in patches: item.start()
            self.addCleanup(lambda: [item.stop() for item in patches])
            evidence = check(str(Path(td) / "gate.json"))
            self.assertFalse(evidence["verified"])


if __name__ == "__main__":
    unittest.main()
