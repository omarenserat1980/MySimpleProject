"""Regression tests for the verified Brain origin attestation gate.

These static tests do not contact a live origin or prove live executor
attestation. They prevent saving BRAIN_ORIGIN when issuer configuration is
missing and ensure the attestation gate precedes the repository write.
"""
from pathlib import Path
import unittest

WORKFLOW = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "brain-configure-verified-origin.yml"
)


class BrainOriginAttestationGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_attestation_status_is_checked_before_origin_is_emitted(self):
        gate = self.workflow.index('get_json("/api/cloud-executor/attestation/status")')
        output = self.workflow.index('f.write("origin=" + value')
        save_step = self.workflow.index("- name: Create or update repository variable")
        self.assertLess(gate, output)
        self.assertLess(output, save_step)

    def test_all_issuer_readiness_fields_are_required(self):
        for requirement in (
            'attestation.get("control_plane_configured") is True',
            'attestation.get("signing_key_present") is True',
            'attestation.get("registry_configured") is True',
            'attestation.get("enrolled_executor_count", 0) > 0',
            'attestation.get("valid_host_binding_count", 0) > 0',
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, self.workflow)

    def test_not_ready_fails_closed_without_saving_origin(self):
        blocked = self.workflow.index(
            "BLOCKED: Cloud Executor attestation configuration is NOT_READY; "
            "BRAIN_ORIGIN was not saved."
        )
        output = self.workflow.index('f.write("origin=" + value')
        self.assertLess(blocked, output)

    def test_live_attestation_is_not_claimed_and_origin_is_not_logged(self):
        self.assertIn('BRAIN_LIVE_ATTESTATION_VERIFIED=NOT_CLAIMED', self.workflow)
        self.assertIn('BRAIN_ORIGIN_NOT_PRINTED=true', self.workflow)
        self.assertNotIn('print("BRAIN_ORIGIN=" + value)', self.workflow)


if __name__ == "__main__":
    unittest.main()
