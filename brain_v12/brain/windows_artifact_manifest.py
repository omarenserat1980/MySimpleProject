"""Validation primitives for authentic Windows image artifact manifests.

This module validates metadata only. It does not download, mount, execute, modify,
or authenticate Windows media. SHA-256 identifies bytes; it does not prove publisher
identity or license eligibility.
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

SCHEMA_VERSION = 1
ALLOWED_FORMATS = frozenset({"iso", "wim", "esd", "vhd", "vhdx"})
SIGNATURE_STATES = frozenset(
    {"NOT_CHECKED", "VERIFIED", "FAILED", "NOT_APPLICABLE"}
)
HEX_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
SAFE_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,199}$")
UTC_SUFFIX = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


def validate_artifact_manifest(manifest: Any) -> dict[str, Any]:
    """Return deterministic validation findings without touching the filesystem."""
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return {"ok": False, "status": "INVALID_MANIFEST", "errors": ["MANIFEST_MUST_BE_OBJECT"]}

    required = (
        "schema_version", "artifact_id", "filename", "format", "size_bytes",
        "sha256", "source_url", "acquired_at_utc", "license_provenance",
        "publisher_signature_status",
    )
    for key in required:
        if key not in manifest:
            errors.append(f"MISSING_{key.upper()}")

    version = manifest.get("schema_version")
    if isinstance(version, bool) or version != SCHEMA_VERSION:
        errors.append("UNSUPPORTED_SCHEMA_VERSION")

    artifact_id = manifest.get("artifact_id")
    if not isinstance(artifact_id, str) or not artifact_id.strip():
        errors.append("ARTIFACT_ID_REQUIRED")

    filename = manifest.get("filename")
    if not isinstance(filename, str) or not SAFE_FILENAME.fullmatch(filename):
        errors.append("INVALID_FILENAME")
    elif filename in {".", ".."} or "/" in filename or "\\\\" in filename:
        errors.append("FILENAME_MUST_BE_BASENAME")

    fmt = manifest.get("format")
    if not isinstance(fmt, str) or fmt.lower() not in ALLOWED_FORMATS:
        errors.append("UNSUPPORTED_FORMAT")
    elif isinstance(filename, str) and "." in filename and filename.rsplit(".", 1)[-1].lower() != fmt.lower():
        errors.append("FORMAT_FILENAME_EXTENSION_MISMATCH")

    size = manifest.get("size_bytes")
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        errors.append("SIZE_BYTES_MUST_BE_POSITIVE_INTEGER")

    digest = manifest.get("sha256")
    if not isinstance(digest, str) or not HEX_SHA256.fullmatch(digest):
        errors.append("INVALID_SHA256")

    source_url = manifest.get("source_url")
    if not isinstance(source_url, str):
        errors.append("SOURCE_URL_REQUIRED")
    else:
        parsed = urlparse(source_url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            errors.append("SOURCE_URL_MUST_BE_HTTPS")

    acquired = manifest.get("acquired_at_utc")
    if not isinstance(acquired, str) or not UTC_SUFFIX.fullmatch(acquired):
        errors.append("ACQUIRED_AT_MUST_BE_UTC_ISO8601")

    provenance = manifest.get("license_provenance")
    if not isinstance(provenance, str) or not provenance.strip():
        errors.append("LICENSE_PROVENANCE_REQUIRED")

    signature = manifest.get("publisher_signature_status")
    if signature not in SIGNATURE_STATES:
        errors.append("INVALID_PUBLISHER_SIGNATURE_STATUS")
    elif signature == "FAILED":
        errors.append("PUBLISHER_SIGNATURE_VERIFICATION_FAILED")

    ok = not errors
    return {
        "ok": ok,
        "status": "MANIFEST_VALID_METADATA_ONLY" if ok else "INVALID_MANIFEST",
        "errors": errors,
        # A manifest claim is not independent proof of publisher authenticity.
        "sha256": digest.lower() if isinstance(digest, str) and HEX_SHA256.fullmatch(digest) else None,
        "artifact_authenticity_verified": False,
        "real_guest_boot_verified": False,
        "execution_performed": False,
    }


def _evidence_matches_artifact(evidence: Any, manifest_result: dict[str, Any]) -> bool:
    return bool(
        isinstance(evidence, dict)
        and evidence.get("status") == "VERIFIED"
        and evidence.get("artifact_sha256")
        and evidence.get("artifact_sha256") == manifest_result.get("sha256")
        and isinstance(evidence.get("evidence_id"), str)
        and evidence["evidence_id"].strip()
    )


def _signature_evidence_is_valid(evidence: Any, manifest_result: dict[str, Any]) -> bool:
    return bool(
        _evidence_matches_artifact(evidence, manifest_result)
        and evidence.get("verification_method") in {"SIGNTOOL_VERIFY", "OS_TRUST_STORE"}
        and isinstance(evidence.get("verifier_identity"), str)
        and evidence.get("verifier_identity").strip()
        and isinstance(evidence.get("signature_subject"), str)
        and evidence.get("signature_subject").strip()
        and evidence.get("signature_result") == "VALID"
        and evidence.get("certificate_chain_result") == "VALID"
        and evidence.get("revocation_result") in {"GOOD", "NOT_SUPPORTED"}
        and isinstance(evidence.get("verified_at_utc"), str)
        and UTC_SUFFIX.fullmatch(evidence.get("verified_at_utc", ""))
    )


def _guest_boot_evidence_is_valid(evidence: Any, manifest_result: dict[str, Any]) -> bool:
    if not _evidence_matches_artifact(evidence, manifest_result):
        return False
    vm_hash = evidence.get("vm_config_sha256")
    return bool(
        evidence.get("source") == "IN_GUEST"
        and evidence.get("os_edition")
        and evidence.get("os_build")
        and evidence.get("boot_time_utc")
        and isinstance(vm_hash, str)
        and HEX_SHA256.fullmatch(vm_hash)
        and evidence.get("independent_verification") is True
    )


def evaluate_artifact_state(
    manifest_result: dict[str, Any],
    *,
    publisher_signature_evidence: dict[str, Any] | None = None,
    image_inspection_evidence: dict[str, Any] | None = None,
    servicing_evidence: dict[str, Any] | None = None,
    guest_boot_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fail closed: caller-supplied JSON fields are not cryptographic verification.

    Evidence records may be shape-checked here, but this module has no trusted
    verifier or attestation signature validation. Consequently it never promotes
    a record to authentic, inspected, serviced, or boot-verified from JSON claims.
    """
    if isinstance(manifest_result, dict) and manifest_result.get("evidence_type") == "SYNTHETIC_SIMULATION_EVENT":
        state = "SIMULATED"
    elif not isinstance(manifest_result, dict) or not manifest_result.get("ok"):
        state = "NOT_VERIFIED"
    else:
        state = "ARTIFACT_FINGERPRINTED"

    return {
        "state": state,
        "signature_evidence_shape_valid": _signature_evidence_is_valid(
            publisher_signature_evidence, manifest_result
        ) if isinstance(manifest_result, dict) else False,
        "inspection_evidence_record_present": _evidence_matches_artifact(
            image_inspection_evidence, manifest_result
        ) if isinstance(manifest_result, dict) else False,
        "servicing_evidence_record_present": _evidence_matches_artifact(
            servicing_evidence, manifest_result
        ) if isinstance(manifest_result, dict) else False,
        "guest_boot_evidence_record_shape_valid": _guest_boot_evidence_is_valid(
            guest_boot_evidence, manifest_result
        ) if isinstance(manifest_result, dict) else False,
        "real_guest_boot_verified": False,
        "physical_hardware_claimed": False,
        "requires_trusted_external_verifier": state == "ARTIFACT_FINGERPRINTED",
    }
