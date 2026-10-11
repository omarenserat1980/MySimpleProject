"""Tests for the read-only Brain emulator audit helper."""
from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from tools import brain_emulator_project_audit as audit_tool


class BrainEmulatorProjectAuditTests(unittest.TestCase):
    def test_audit_never_serializes_secret_values(self):
        sentinel = "DO_NOT_LEAK_BRAIN_SECRET_TEST_VALUE"
        with patch.dict(os.environ, {"BRAIN_CLOUD_EXECUTOR_TOKEN": sentinel}):
            with patch.object(audit_tool, "run_version", return_value={"available": False, "version": ""}):
                with patch.object(audit_tool.shutil, "which", return_value=None):
                    report = audit_tool.audit()
        rendered = json.dumps(report, ensure_ascii=False)
        self.assertNotIn(sentinel, rendered)
        self.assertFalse(report["boot_path"]["secret_values_disclosed"])
        self.assertTrue(report["boot_path"]["local_environment_presence_only"]["BRAIN_CLOUD_EXECUTOR_TOKEN"])

    def test_qemu_path_does_not_require_a_terraform_or_opennebula_provider(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("BRAIN_WINDOWS_CLOUD_PROVIDER", None)
            with patch.object(audit_tool, "run_version", return_value={"available": False, "version": ""}):
                with patch.object(audit_tool.shutil, "which", return_value=None):
                    report = audit_tool.audit()
        self.assertEqual(report["boot_path"]["provider_configuration"], "NOT_SET_QEMU_PATH_MAY_BE_USED")
        self.assertNotIn("CLOUD_WINDOWS_PROVIDER_NOT_CONFIGURED", report["boot_path"]["blockers"])

    def test_audit_declares_guest_evidence_acceptance_rule(self):
        with patch.object(audit_tool, "run_version", return_value={"available": False, "version": ""}):
            with patch.object(audit_tool.shutil, "which", return_value=None):
                report = audit_tool.audit()
        self.assertTrue(report["acceptance_rule"]["qemu_started_or_workflow_green_is_not_boot_proof"])
        self.assertTrue(any("WINDOWS_BOOT_VERIFIED" in item for item in report["acceptance_rule"]["required"]))


if __name__ == "__main__":
    unittest.main()
