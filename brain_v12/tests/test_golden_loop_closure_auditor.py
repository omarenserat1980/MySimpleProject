import unittest

from brain_v12.brain.golden_loop_closure_auditor import (
    REQUIRED_RUNNER_LABELS,
    audit_snapshot,
)


def complete_snapshot():
    commit = "a" * 40
    return {
        "repository": {"commit_sha": commit, "required_ci_passed": True, "source_commit_bound": True},
        "runner": {
            "secret_configured": True, "api_read_succeeded": True, "online": True,
            "execution_probe_passed": True, "runtime_surface_passed": True,
            "labels": sorted(REQUIRED_RUNNER_LABELS),
        },
        "contract": {
            "control_plane_issued": True, "signature_verified": True,
            "source_commit_matches": True, "lease_valid": True, "not_expired": True,
            "capability_authorized": True, "source_commit_sha": commit,
        },
        "executor": {"attestation_verified": True, "same_runner_as_boot": True, "qemu_kvm_available": True},
        "windows": {
            "iso_validated": True, "installed_disk_boot_verified": True,
            "guest_identity_verified": True, "guest_health_verified": True, "reality": "REAL",
        },
        "evidence": {
            "hashes_verified": True, "independent_verifier_passed": True,
            "persisted_and_reopen_verified": True, "source_commit_sha": commit,
        },
        "recovery": {"restart_recovery_tested": True, "idempotency_verified": True, "rollback_ready": True},
        "governance": {
            "owner_approval_verified": True, "cost_gate_passed": True, "stop_switch_tested": True,
        },
    }


class GoldenLoopClosureAuditorTests(unittest.TestCase):
    def test_complete_real_evidence_snapshot_passes(self):
        report = audit_snapshot(complete_snapshot())
        self.assertTrue(report["ok"])
        self.assertEqual(report["status"], "GOLDEN_LOOP_READY_FOR_CLOSURE")
        self.assertEqual(report["blockers"], [])

    def test_missing_runner_secret_blocks(self):
        snapshot = complete_snapshot()
        snapshot["runner"]["secret_configured"] = False
        report = audit_snapshot(snapshot)
        self.assertFalse(report["ok"])
        self.assertIn("RUNNER_SECRET_CONFIGURED_REQUIRED", report["blockers"])

    def test_simulated_twin_never_counts_as_real_boot(self):
        snapshot = complete_snapshot()
        snapshot["windows"]["reality"] = "SIMULATED"
        report = audit_snapshot(snapshot)
        self.assertFalse(report["ok"])
        self.assertIn("REAL_WINDOWS_EVIDENCE_REQUIRED", report["blockers"])

    def test_ci_success_does_not_replace_guest_evidence(self):
        snapshot = complete_snapshot()
        snapshot["windows"]["installed_disk_boot_verified"] = False
        report = audit_snapshot(snapshot)
        self.assertFalse(report["ok"])
        self.assertIn("WINDOWS_INSTALLED_DISK_BOOT_VERIFIED_REQUIRED", report["blockers"])

    def test_string_true_is_not_accepted_as_boolean_proof(self):
        snapshot = complete_snapshot()
        snapshot["contract"]["signature_verified"] = "true"
        report = audit_snapshot(snapshot)
        self.assertFalse(report["ok"])
        self.assertIn("CONTRACT_SIGNATURE_VERIFIED_REQUIRED", report["blockers"])

    def test_evidence_commit_mismatch_blocks(self):
        snapshot = complete_snapshot()
        snapshot["evidence"]["source_commit_sha"] = "b" * 40
        report = audit_snapshot(snapshot)
        self.assertFalse(report["ok"])
        self.assertIn("EVIDENCE_SOURCE_COMMIT_MISMATCH", report["blockers"])

    def test_missing_required_runner_label_blocks(self):
        snapshot = complete_snapshot()
        snapshot["runner"]["labels"].remove("qemu")
        report = audit_snapshot(snapshot)
        self.assertFalse(report["ok"])
        self.assertIn("RUNNER_REQUIRED_LABELS_MISSING", report["blockers"])

    def test_malformed_snapshot_fails_closed(self):
        report = audit_snapshot([])
        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "GOLDEN_LOOP_BLOCKED")


if __name__ == "__main__":
    unittest.main()
