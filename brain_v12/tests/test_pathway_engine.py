import unittest

from brain_v12.brain.pathway_engine import evaluate_pathway


def ev(**kwargs):
    return {
        "verified": True,
        "evidence_id": "ev-1",
        "source": "test",
        "observed_at": "2026-10-11T00:00:00Z",
        "evidence_sha256": "a" * 64,
        "verifier_id": "unit-test-verifier",
        "verification_method": "unit-test",
        "verification_ref": "test://evidence/ev-1",
        **kwargs,
    }


class PathwayEngineTests(unittest.TestCase):
    def test_missing_evidence_blocks_and_selects_first_gate(self):
        result = evaluate_pathway("code_delivery", {})
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["next_gate"], "source_snapshot")

    def test_all_generic_gates_verified_is_ready(self):
        ids = ["source_snapshot", "plan_reviewed", "tests_passed", "security_review", "verification_evidence", "integration_verified"]
        result = evaluate_pathway("code_delivery", {key: ev() for key in ids})
        self.assertTrue(result["ready"])
        self.assertEqual(result["blockers"], [])

    def test_evidence_requires_sha256_digest(self):
        item = ev()
        item.pop("evidence_sha256")
        result = evaluate_pathway("code_delivery", {"source_snapshot": item})
        self.assertEqual(result["gates"][0]["reason"], "EVIDENCE_HASH_MISSING")

    def test_evidence_rejects_malformed_sha256_digest(self):
        result = evaluate_pathway("code_delivery", {"source_snapshot": ev(evidence_sha256="not-a-digest")})
        self.assertEqual(result["gates"][0]["reason"], "EVIDENCE_HASH_INVALID")

    def test_evidence_requires_verification_provenance(self):
        item = ev()
        item.pop("verifier_id")
        result = evaluate_pathway("code_delivery", {"source_snapshot": item})
        self.assertEqual(result["gates"][0]["reason"], "EVIDENCE_VERIFICATION_PROVENANCE_INCOMPLETE")

    def test_windows_contract_requires_real_signature_validation(self):
        result = evaluate_pathway("windows_real_boot", {"signed_contract": ev(signature_valid=False)})
        self.assertFalse(result["ready"])
        self.assertEqual(result["gates"][0]["reason"], "CONTRACT_SIGNATURE_NOT_VERIFIED")

    def test_windows_boot_must_be_from_installed_disk_and_correct_os(self):
        result = evaluate_pathway("windows_real_boot", {"guest_boot": ev(os_name="Windows Server 2025", boot_source="ISO")})
        self.assertEqual(result["gates"][4]["reason"], "INSTALLED_DISK_BOOT_NOT_PROVEN")

    def test_same_run_mismatch_blocks(self):
        result = evaluate_pathway("windows_real_boot", {
            "same_run_binding": ev(run_id="run-2", contract_id="contract-1", installed_disk_id="disk-1")
        }, expected_run_id="run-1")
        self.assertEqual(result["gates"][5]["reason"], "WORKFLOW_RUN_MISMATCH")

    def test_windows_gates_reject_evidence_from_another_run(self):
        result = evaluate_pathway("windows_real_boot", {
            "signed_contract": ev(signature_valid=True, run_id="run-old")
        }, expected_run_id="run-current")
        self.assertEqual(result["gates"][0]["reason"], "WORKFLOW_RUN_MISMATCH")

    def test_windows_gates_require_run_id_when_expected(self):
        result = evaluate_pathway("windows_real_boot", {
            "signed_contract": ev(signature_valid=True)
        }, expected_run_id="run-current")
        self.assertEqual(result["gates"][0]["reason"], "WORKFLOW_RUN_ID_MISSING")

    def test_trusted_executor_requires_full_trust_chain(self):
        result = evaluate_pathway("windows_real_boot", {"trusted_executor": ev(attestation_valid=True)})
        self.assertEqual(result["gates"][1]["reason"], "EXECUTOR_TRUST_CHAIN_INCOMPLETE")

    def test_external_publication_requires_explicit_authorization(self):
        result = evaluate_pathway("media_factory", {"publish_authorization": ev(authorized=False)})
        self.assertEqual(result["gates"][-1]["reason"], "PUBLICATION_NOT_AUTHORIZED")

    def test_unknown_pathway_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_pathway("made_up", {})


if __name__ == "__main__":
    unittest.main()
