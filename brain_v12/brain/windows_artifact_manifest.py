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
        # A manifest claim is not independent proof of publisher authenticity.\n        "artifact_authenticity_verified": False,
        "real_guest_boot_verified": False,
        "execution_performed": False,
    }


def evaluate_artifact_state(
    manifest_result: dict[str, Any],
    *,
    image_inspected: bool = False,
    image_serviced: bool = False,
    guest_boot_evidence_verified: bool = False,
) -> dict[str, Any]:
    """Derive a conservative state; metadata validity alone never proves a boot."""
    if not isinstance(manifest_result, dict) or not manifest_result.get("ok"):
        state = "NOT_VERIFIED"
    elif manifest_result.get("artifact_authenticity_verified") is True:
        state = "ARTIFACT_AUTHENTICITY_VERIFIED"
    else:
        state = "ARTIFACT_FINGERPRINTED"

    if state == "ARTIFACT_AUTHENTICITY_VERIFIED" and image_inspected:
        state = "IMAGE_INSPECTED"
    if state == "IMAGE_INSPECTED" and image_serviced:
        state = "IMAGE_SERVICED"
    if state == "IMAGE_SERVICED" and guest_boot_evidence_verified:
        state = "GUEST_BOOT_VERIFIED"

    # Explicitly prevent promotion from simulated evidence.
    if manifest_result.get("evidence_type") == "SYNTHETIC_SIMULATION_EVENT":
        state = "SIMULATED"

    return {
        "state": state,
        "real_guest_boot_verified": state == "GUEST_BOOT_VERIFIED",
        "physical_hardware_claimed": False,
    }
