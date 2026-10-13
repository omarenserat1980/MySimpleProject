import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain_v12.tools.windows_boot_proof import verify_boot


class WindowsBootProofTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.evidence = {
            "schema": "BRAIN-WINDOWS-BOOT-EVIDENCE-1",
            "status": "WINDOWS_BOOT_VERIFIED",
            "guest": {"os": "Windows Server 2025", "architecture": "x86_64", "boot_verified": True},
            "media": {"sha256": "a" * 64},
            "uefi": {"ready": True},
            "cpu": {"x86_64": True},
            "network": {"adapter_up": True, "internet_443": True},
            "storage": {"filesystem": "NTFS", "size_bytes": 64 * 1024**3},
            "control": {
                "schema": "brain.windows-execution-contract.v1", "status": "VERIFIED",
                "capability": "windows-server-2025-real-boot", "executor": "windows-real-boot-qemu",
                "brain_id": "brain-test", "generation": 1, "fencing_token": 1,
                "task_id": "task-test", "attempt_id": "attempt-test",
            },
            "executor": {"verified": True, "executor_id": "exec-1", "hostname": "host-1",
                         "evidence_ref": "evidence-1", "runner_name": "runner-1",
                         "workflow_run_id": "123"},
            "boot_source": "windows-installed-disk",
            "qemu_status": "QEMU_EXITED_AFTER_VERIFIED_BOOT",
        }
        self.contract = {"verified": True, "contract": dict(self.evidence["control"])}
        self.executor = {"verified": True, "executor_id": "exec-1", "evidence_ref": "evidence-1"}
        self.raw_guest = {
            "schema": "BRAIN-WINDOWS-BOOT-EVIDENCE-1",
            "status": "WINDOWS_BOOT_VERIFIED",
            "guest": {"os": "Windows Server 2025", "architecture": "AMD64",
                      "boot_verified": True, "boot_time": "2026-10-13T12:00:00Z",
                      "version": "10.0", "build": "26100"},
            "network": {"adapter_up": True, "internet_443": True},
            "storage": {"filesystem": "NTFS", "size_bytes": 64 * 1024**3},
        }
        self._write("guest-evidence.json", self.raw_guest)
        self._write("evidence.json", self.evidence)
        self._write("contract.json", self.contract)
        self._write("executor.json", self.executor)
        (self.root / "marker.txt").write_text("WINDOWS_BOOT_VERIFIED\n", encoding="utf-8")
        (self.root / "phase.txt").write_text(
            "BOOT_PHASE=WINDOWS_INSTALLED_AND_BOOTED_FROM_DISK\n"
            "BOOT_SOURCE=windows-installed-disk\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def _write(self, name, value):
        (self.root / name).write_text(json.dumps(value), encoding="utf-8")

    def _verify(self, **overrides):
        args = dict(
            evidence_path=self.root / "evidence.json", marker_path=self.root / "marker.txt",
            phase_path=self.root / "phase.txt", contract_gate_path=self.root / "contract.json",
            executor_gate_path=self.root / "executor.json", expected_run_id="123",
            guest_evidence_path=self.root / "guest-evidence.json",
            trusted_iso_sha256="a" * 64)
        args.update(overrides)
        return verify_boot(**args)

    def test_valid_same_run_installed_disk_evidence_passes(self):
        with patch("brain_v12.tools.windows_boot_proof.WindowsCompletionGate.verify",
                   return_value={"verified": True, "status": "WINDOWS_BOOT_VERIFIED", "reasons": []}):
            result = self._verify()
        self.assertTrue(result["verified"], result)
        self.assertEqual(result["status"], "WINDOWS_BOOT_VERIFIED")

    def test_missing_marker_fails_closed(self):
        (self.root / "marker.txt").write_text("QEMU_STARTED", encoding="utf-8")
        result = self._verify()
        self.assertFalse(result["verified"])
        self.assertIn("GUEST_BOOT_MARKER_INVALID", result["reasons"])

    def test_wrong_run_id_fails_closed(self):
        result = self._verify(expected_run_id="999")
        self.assertFalse(result["verified"])
        self.assertIn("WORKFLOW_RUN_ID_MISMATCH", result["reasons"])

    def test_contract_gate_failure_fails_closed(self):
        self._write("contract.json", {"verified": False, "contract": {}})
        result = self._verify()
        self.assertFalse(result["verified"])
        self.assertIn("CONTRACT_GATE_NOT_VERIFIED", result["reasons"])

    def test_executor_identity_mismatch_fails_closed(self):
        self._write("executor.json", {"verified": True, "executor_id": "other", "evidence_ref": "other-ref"})
        result = self._verify()
        self.assertFalse(result["verified"])
        self.assertIn("EXECUTOR_ID_MISMATCH", result["reasons"])

    def test_raw_guest_evidence_is_required_and_validated(self):
        self.raw_guest["guest"]["boot_verified"] = False
        self._write("guest-evidence.json", self.raw_guest)
        result = self._verify()
        self.assertFalse(result["verified"])
        self.assertIn("RAW_GUEST_OS_BOOT_NOT_PROVEN", result["reasons"])

    def test_trusted_iso_hash_must_match_combined_evidence(self):
        result = self._verify(trusted_iso_sha256="b" * 64)
        self.assertFalse(result["verified"])
        self.assertIn("TRUSTED_ISO_SHA256_MISMATCH", result["reasons"])

    def test_completion_gate_failure_fails_closed(self):
        with patch("brain_v12.tools.windows_boot_proof.WindowsCompletionGate.verify",
                   return_value={"verified": False, "status": "INCOMPLETE", "reasons": ["GUEST_BOOT_NOT_VERIFIED"]}):
            result = self._verify()
        self.assertFalse(result["verified"])
        self.assertIn("COMPLETION_GATE:GUEST_BOOT_NOT_VERIFIED", result["reasons"])


if __name__ == "__main__":
    unittest.main()
