"""Static safety-contract tests for the Windows Cloud Launch workflow.

These tests do not contact Azure or prove a VM booted; they guard workflow
control-flow invariants that prevent accidental provisioning.
"""
from pathlib import Path
import unittest

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "brain-windows-cloud-launch.yml"


class WindowsCloudWorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_approved_apply_fails_closed_when_admin_secrets_missing(self):
        self.assertIn("BLOCKED_CONFIGURATION: approved deployment is missing required Windows administrator secrets.", self.workflow)
        self.assertIn('exit 2', self.workflow)
        self.assertIn("CHECK_WINDOWS_ADMIN_USERNAME CHECK_WINDOWS_ADMIN_PASSWORD", self.workflow)

    def test_state_bootstrap_is_gated_by_apply_enabled(self):
        self.assertIn('if: ${{ steps.config.outputs.apply_enabled == \'true\' }}', self.workflow)
        self.assertIn("Bootstrap remote Terraform state", self.workflow)

    def test_vm_deployment_is_gated_by_apply_enabled(self):
        self.assertIn("Deploy and verify Windows Server 2025", self.workflow)
        self.assertIn('if: ${{ steps.config.outputs.apply_enabled == \'true\' }}', self.workflow)

    def test_preflight_only_is_explicitly_non_provisioning(self):
        self.assertIn("Preflight only. No state storage or VM resources were created.", self.workflow)
        self.assertIn('default: false', self.workflow)


if __name__ == "__main__":
    unittest.main()
