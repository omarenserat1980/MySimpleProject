"""Focused tests for the metadata-only Windows artifact manifest gate."""
import unittest

from brain_v12.brain.windows_artifact_manifest import (
    evaluate_artifact_state,
    validate_artifact_manifest,
)


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
                result, publisher_signature_independently_verified=True
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

    def test_synthetic_evidence_never_promotes_to_real_boot(self):
        result = validate_artifact_manifest(valid_manifest())
        state = evaluate_artifact_state(
            result,
            publisher_signature_independently_verified=True,
            image_inspected=True,
            image_serviced=True,
            guest_boot_evidence_verified=True,
        )
        self.assertEqual(state["state"], "GUEST_BOOT_VERIFIED")
        self.assertTrue(state["real_guest_boot_verified"])

        simulated = evaluate_artifact_state(
            {**result, "evidence_type": "SYNTHETIC_SIMULATION_EVENT"},
            publisher_signature_independently_verified=True,
            image_inspected=True,
            image_serviced=True,
            guest_boot_evidence_verified=True,
        )
        self.assertEqual(simulated["state"], "SIMULATED")
        self.assertFalse(simulated["real_guest_boot_verified"])

    def test_bool_is_not_accepted_as_integer_size(self):
        result = validate_artifact_manifest(valid_manifest(size_bytes=True))
        self.assertFalse(result["ok"])
        self.assertIn("SIZE_BYTES_MUST_BE_POSITIVE_INTEGER", result["errors"])


if __name__ == "__main__":
    unittest.main()
