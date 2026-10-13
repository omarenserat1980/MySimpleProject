from __future__ import annotations

import unittest

from brain_v12.brain.family_governance import FamilyApproval, FamilyGovernance


class FamilyGovernanceTests(unittest.TestCase):
    def setUp(self):
        self.gate = FamilyGovernance()

    def test_low_risk_reversible_action_does_not_need_family_approval(self):
        result = self.gate.evaluate("health_check", risk="low")
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "ALLOWED_LOW_RISK")
        self.assertFalse(result["approval_required"])

    def test_high_risk_action_requires_family_approval(self):
        result = self.gate.evaluate("publish", risk="high")
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "FAMILY_APPROVAL_REQUIRED")
        self.assertTrue(result["approval_required"])

    def test_only_verified_guardian_approval_scoped_to_action_is_accepted(self):
        approval = FamilyApproval(
            approver_role="FAMILY_GUARDIAN",
            approved=True,
            consent_reference="consent-001",
            identity_verified=True,
            scope="publish",
        )
        result = self.gate.evaluate("publish", risk="high", approval=approval)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "FAMILY_APPROVED")

    def test_member_or_unverified_approval_is_rejected(self):
        for role, verified in (("FAMILY_MEMBER", True), ("FAMILY_GUARDIAN", False)):
            approval = FamilyApproval(
                approver_role=role, approved=True, consent_reference="consent-002",
                identity_verified=verified, scope="delete",
            )
            result = self.gate.evaluate("delete", approval=approval)
            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], "FAMILY_APPROVAL_INVALID_OR_OUT_OF_SCOPE")

    def test_approval_cannot_override_scope_or_safety_denial(self):
        wrong_scope = FamilyApproval(
            approver_role="FAMILY_GUARDIAN", approved=True,
            consent_reference="consent-003", identity_verified=True, scope="publish",
        )
        result = self.gate.evaluate("delete", approval=wrong_scope)
        self.assertFalse(result["ok"])
        denied = self.gate.evaluate("bypass_safety_gate", approval=wrong_scope)
        self.assertFalse(denied["ok"])
        self.assertEqual(denied["status"], "POLICY_DENY")

    def test_family_approval_does_not_enable_real_os_boot(self):
        approval = FamilyApproval(
            approver_role="FAMILY_GUARDIAN", approved=True,
            consent_reference="consent-004", identity_verified=True, scope="real_os_boot",
        )
        result = self.gate.evaluate("real_os_boot", approval=approval, simulation_only=True)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "SIMULATION_ONLY")
        self.assertFalse(result["real_windows_boot_verified"])
        outside_simulation = self.gate.evaluate("real_os_boot", approval=approval, simulation_only=False)
        self.assertFalse(outside_simulation["ok"])
        self.assertEqual(outside_simulation["status"], "SEPARATE_EXECUTION_GATE_REQUIRED")

    def test_irreversible_action_requires_approval_even_if_low_risk_label(self):
        result = self.gate.evaluate("workspace_change", risk="low", irreversible=True)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "FAMILY_APPROVAL_REQUIRED")


if __name__ == "__main__":
    unittest.main()
