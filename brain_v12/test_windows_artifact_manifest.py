"""Focused tests for the metadata-only Windows artifact manifest gate."""
import unittest

from brain_v12.brain.windows_artifact_manifest import (
    evaluate_artifact_state,
    validate_artifact_manifest,
)


def signature_evidence(result):
    return {"status": "VERIFIED", "evidence_id": "signature-1",
            "artifact_sha256": result["sha256"], "verification_method": "OS_TRUST_STORE",
            "verifier_identity": "test-verifier", "signature_subject": "Microsoft Corporation",
            "signature_result": "VALID", "certificate_chain_result": "VALID",
            "revocation_result": "GOOD", "verified_at_utc": "2026-10-18T10:30:00Z"}


def valid_manifest(**overrides):
    manifest = {
        "schema_version": 1,
        "artifact_id": "ws2025-eval-x64",
        "filename": "WindowsServer2025.iso",
        "format": "iso",
        "size_bytes": 1024,
        "sha256": "a" * 64,
        "source_url": "https://www.microsoft.com/en-us/evalcenter/",
        "acquired_at_utc": "2026-10-18T10:00:00Z",
        "license_provenance": "Official evaluation media; terms must be reviewed",
        "publisher_signature_status": "NOT_CHECKED",
    }
    manifest.update(overrides)
    return manifest


class WindowsArtifactManifestTests(unittest.TestCase):
    def test_valid_metadata_does_not_claim_authenticity_or_boot(self):
        result = validate_artifact_manifest(valid_manifest())
        self.assertTrue(result["ok"])
        self.assertFalse(result["artifact_authenticity_verified"])
        self.assertFalse(result["real_guest_boot_verified"])
        self.assertEqual(
            evaluate_artifact_state(result)["state"], "ARTIFACT_FINGERPRINTED"
        )

    def test_manifest_cannot_self_assert_signature_verification(self):
        result = validate_artifact_manifest(
            valid_manifest(publisher_signature_status="VERIFIED")
        )
        self.assertTrue(result["ok"])
        self.assertFalse(result["artifact_authenticity_verified"])
        self.assertEqual(
            evaluate_artifact_state(result)["state"], "ARTIFACT_FINGERPRINTED"
        )

    def test_independent_signature_evidence_is_required_for_authenticity_state(self):
        result = validate_artifact_manifest(valid_manifest())
        self.assertEqual(
            evaluate_artifact_state(
                result, publisher_signature_evidence=signature_evidence(result)
            )["state"],
            "ARTIFACT_AUTHENTICITY_VERIFIED",
        )

    def test_signature_evidence_missing_verifier_identity_cannot_promote_state(self):
        result = validate_artifact_manifest(valid_manifest())
        evidence = signature_evidence(result)
        evidence.pop("verifier_identity")
        self.assertEqual(
            evaluate_artifact_state(result, publisher_signature_evidence=evidence)["state"],
            "ARTIFACT_FINGERPRINTED",
        )

    def test_signature_evidence_for_different_artifact_cannot_promote_state(self):
        result = validate_artifact_manifest(valid_manifest())
        evidence = signature_evidence(result)
        evidence["artifact_sha256"] = "b" * 64
        self.assertEqual(
            evaluate_artifact_state(result, publisher_signature_evidence=evidence)["state"],
            "ARTIFACT_FINGERPRINTED",
        )

    def test_signature_evidence_with_invalid_certificate_chain_is_rejected(self):
        result = validate_artifact_manifest(valid_manifest())
        evidence = signature_evidence(result)
        evidence["certificate_chain_result"] = "INVALID"
        self.assertEqual(
            evaluate_artifact_state(result, publisher_signature_evidence=evidence)["state"],
            "ARTIFACT_FINGERPRINTED",
        )

    def test_signature_evidence_with_untrusted_verification_method_is_rejected(self):
        result = validate_artifact_manifest(valid_manifest())
        evidence = signature_evidence(result)
        evidence["verification_method"] = "USER_ASSERTION"
        self.assertEqual(
            evaluate_artifact_state(result, publisher_signature_evidence=evidence)["state"],
            "ARTIFACT_FINGERPRINTED",
        )

    def test_image_inspection_requires_matching_evidence_record(self):
        result = validate_artifact_manifest(valid_manifest())
        self.assertEqual(
            evaluate_artifact_state(
                result,
                publisher_signature_evidence=signature_evidence(result),
                image_inspection_evidence={"status": "VERIFIED", "evidence_id": "inspection-1",
                                           "artifact_sha256": result["sha256"]},
            )["state"],
            "IMAGE_INSPECTED",
        )
        self.assertEqual(
            evaluate_artifact_state(
                result,
                publisher_signature_evidence=signature_evidence(result),
                image_inspection_evidence={"status": "VERIFIED", "evidence_id": "inspection-1",
                                           "artifact_sha256": "b" * 64},
            )["state"],
            "ARTIFACT_AUTHENTICITY_VERIFIED",
        )

    def test_invalid_digest_is_rejected(self):
        result = validate_artifact_manifest(valid_manifest(sha256="xyz"))
        self.assertFalse(result["ok"])
        self.assertIn("INVALID_SHA256", result["errors"])
        self.assertEqual(evaluate_artifact_state(result)["state"], "NOT_VERIFIED")

    def test_http_source_is_rejected(self):
        result = validate_artifact_manifest(
            valid_manifest(source_url="http://example.com/image.iso")
        )
        self.assertFalse(result["ok"])
        self.assertIn("SOURCE_URL_MUST_BE_HTTPS", result["errors"])

    def test_format_extension_mismatch_is_rejected(self):
        result = validate_artifact_manifest(
            valid_manifest(filename="WindowsServer2025.vhdx", format="iso")
        )
        self.assertFalse(result["ok"])
        self.assertIn("FORMAT_FILENAME_EXTENSION_MISMATCH", result["errors"])

    def test_failed_publisher_signature_is_rejected(self):
        result = validate_artifact_manifest(
            valid_manifest(publisher_signature_status="FAILED")
        )
        self.assertFalse(result["ok"])
        self.assertIn("PUBLISHER_SIGNATURE_VERIFICATION_FAILED", result["errors"])

    def test_guest_boot_requires_matching_in_guest_evidence(self):
        result = validate_artifact_manifest(valid_manifest())
        inspection = {"status": "VERIFIED", "evidence_id": "inspection-1",
                      "artifact_sha256": result["sha256"]}
        servicing = {"status": "VERIFIED", "evidence_id": "servicing-1",
                     "artifact_sha256": result["sha256"]}
        guest = {"status": "VERIFIED", "evidence_id": "guest-1",
                 "artifact_sha256": result["sha256"], "source": "IN_GUEST",
                 "os_edition": "Windows Server 2025 Evaluation", "os_build": "test-build",
                 "boot_time_utc": "2026-10-18T10:30:00Z", "vm_config_sha256": "c" * 64,
                 "independent_verification": True}
        state = evaluate_artifact_state(
            result, publisher_signature_evidence=signature_evidence(result),
            image_inspection_evidence=inspection, servicing_evidence=servicing,
            guest_boot_evidence=guest,
        )
        self.assertEqual(state["state"], "GUEST_BOOT_VERIFIED")
        self.assertTrue(state["real_guest_boot_verified"])

        simulated = evaluate_artifact_state(
            {**result, "evidence_type": "SYNTHETIC_SIMULATION_EVENT"},
            publisher_signature_evidence=signature_evidence(result),
            image_inspection_evidence=inspection, servicing_evidence=servicing,
            guest_boot_evidence=guest,
        )
        self.assertEqual(simulated["state"], "SIMULATED")
        self.assertFalse(simulated["real_guest_boot_verified"])

    def test_guest_boot_evidence_must_match_artifact_and_be_in_guest(self):
        result = validate_artifact_manifest(valid_manifest())
        inspection = {"status": "VERIFIED", "evidence_id": "inspection-1",
                      "artifact_sha256": result["sha256"]}
        servicing = {"status": "VERIFIED", "evidence_id": "servicing-1",
                     "artifact_sha256": result["sha256"]}
        guest = {"status": "VERIFIED", "evidence_id": "guest-1",
                 "artifact_sha256": "d" * 64, "source": "SIMULATOR",
                 "os_edition": "Windows Server 2025 Evaluation", "os_build": "test-build",
                 "boot_time_utc": "2026-10-18T10:30:00Z", "vm_config_sha256": "c" * 64,
                 "independent_verification": True}
        state = evaluate_artifact_state(
            result, publisher_signature_evidence=signature_evidence(result),
            image_inspection_evidence=inspection, servicing_evidence=servicing,
            guest_boot_evidence=guest,
        )
        self.assertEqual(state["state"], "IMAGE_SERVICED")
        self.assertFalse(state["real_guest_boot_verified"])

    def test_bool_is_not_accepted_as_integer_size(self):
        result = validate_artifact_manifest(valid_manifest(size_bytes=True))
        self.assertFalse(result["ok"])
        self.assertIn("SIZE_BYTES_MUST_BE_POSITIVE_INTEGER", result["errors"])


if __name__ == "__main__":
    unittest.main()
