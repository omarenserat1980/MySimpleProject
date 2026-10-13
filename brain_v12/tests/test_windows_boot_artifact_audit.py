import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from brain_v12.tools.audit_windows_boot_artifact import REQUIRED, audit_artifact


class WindowsBootArtifactAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.zip_path = self.root / "artifact.zip"

    def tearDown(self):
        self.tmp.cleanup()

    def _build(self, installed_disk=True, completion=True, executor=True):
        evidence = {
            "schema": "BRAIN-WINDOWS-BOOT-EVIDENCE-1",
            "status": "WINDOWS_BOOT_VERIFIED" if installed_disk else "INSTALLER_STARTED",
            "guest": {"os": "Windows Server 2025", "boot_verified": installed_disk},
            "boot_source": "windows-installed-disk" if installed_disk else "iso-installer",
            "executor": {"workflow_run_id": "42"},
        }
        phase = ("BOOT_PHASE=WINDOWS_INSTALLED_AND_BOOTED_FROM_DISK\n"
                 "BOOT_SOURCE=windows-installed-disk\n") if installed_disk else "BOOT_PHASE=INSTALLER_STARTED\n"
        values = {
            "windows-boot-evidence.json": json.dumps(evidence),
            "windows-completion-gate.json": json.dumps({
                "verified": completion, "status": "WINDOWS_BOOT_VERIFIED" if completion else "INCOMPLETE"}),
            "windows-boot-proof.json": json.dumps({
                "verified": installed_disk and completion and executor,
                "status": "WINDOWS_BOOT_VERIFIED" if installed_disk and completion and executor else "INCOMPLETE",
                "workflow_run_id": "42"}),
            "windows-boot-phase.txt": phase,
            "WINDOWS_BOOT_VERIFIED": "WINDOWS_BOOT_VERIFIED\n" if installed_disk else "INSTALLER_STARTED\n",
            "cloud-executor-gate.json": json.dumps({"verified": executor}),
        }
        with zipfile.ZipFile(self.zip_path, "w") as z:
            for name in REQUIRED:
                z.writestr(name, values[name])

    def test_installer_only_artifact_is_rejected(self):
        self._build(installed_disk=False, completion=False)
        result = audit_artifact(self.zip_path, "42")
        self.assertFalse(result["verified"])
        self.assertEqual(result["status"], "NO_GO")
        self.assertIn("BOOT_SOURCE_NOT_INSTALLED_DISK", result["reasons"])
        self.assertIn("INSTALLED_DISK_PHASE_MISSING", result["reasons"])

    def test_missing_cloud_executor_gate_is_rejected(self):
        self._build(executor=False)
        result = audit_artifact(self.zip_path, "42")
        self.assertFalse(result["verified"])
        self.assertIn("CLOUD_EXECUTOR_GATE_NOT_PASSED", result["reasons"])

    def test_completion_gate_failure_is_rejected(self):
        self._build(completion=False)
        result = audit_artifact(self.zip_path, "42")
        self.assertFalse(result["verified"])
        self.assertIn("COMPLETION_GATE_NOT_PASSED", result["reasons"])

    def test_wrong_run_id_is_rejected(self):
        self._build()
        result = audit_artifact(self.zip_path, "99")
        self.assertFalse(result["verified"])
        self.assertIn("WORKFLOW_RUN_ID_MISMATCH", result["reasons"])

    def test_complete_same_run_artifact_passes(self):
        self._build()
        result = audit_artifact(self.zip_path, "42")
        self.assertTrue(result["verified"], result)
        self.assertEqual(result["status"], "WINDOWS_BOOT_VERIFIED")


if __name__ == "__main__":
    unittest.main()
