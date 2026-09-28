"""License gate for external visual media used by the cinematic factory.

This module does not declare an image "legal" merely because it is online.
External images must carry explicit provenance/license metadata. AI-generated,
CC0/public-domain, or otherwise explicitly licensed commercial/derivative media
can pass according to policy; unknown licensing is rejected.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

ALLOWED_SOURCE_TYPES = {"ai_generated", "cc0", "public_domain", "licensed"}
NON_COMMERCIAL = {"cc_by_nc", "cc_by_nc_sa", "cc_by_nc_nd"}
NO_DERIVATIVES = {"cc_by_nd", "cc_by_nc_nd"}

@dataclass(frozen=True)
class LicenseDecision:
    allowed: bool
    reason: str
    normalized_license: str

def check_media_license(media: dict[str, Any]) -> LicenseDecision:
    source_type = str(media.get("image_source_type", "ai_generated")).strip().lower()
    license_name = str(media.get("license", "unknown")).strip().lower().replace(" ", "_")
    external_url = str(media.get("image_reference_url", "")).strip()

    # No external image: generated/original visual prompt is not blocked here.
    if not external_url:
        return LicenseDecision(True, "no_external_image_reference", license_name)

    if source_type not in ALLOWED_SOURCE_TYPES:
        return LicenseDecision(False, "external_image_source_type_not_allowlisted", license_name)

    if license_name in NON_COMMERCIAL:
        return LicenseDecision(False, "license_not_commercial", license_name)

    if license_name in NO_DERIVATIVES:
        return LicenseDecision(False, "license_disallows_derivatives", license_name)

    if source_type in {"cc0", "public_domain"}:
        return LicenseDecision(True, "public_reuse_category", license_name)

    if source_type == "ai_generated":
        return LicenseDecision(True, "ai_generated_or_original", license_name)

    if source_type == "licensed":
        commercial = str(media.get("commercial_use", "")).strip().lower() in {"1","true","yes","allowed"}
        derivatives = str(media.get("derivatives", "")).strip().lower() in {"1","true","yes","allowed"}
        if commercial and derivatives:
            return LicenseDecision(True, "explicit_commercial_derivative_license", license_name)
        return LicenseDecision(False, "licensed_media_missing_commercial_or_derivative_permission", license_name)

    return LicenseDecision(False, "unknown_license_status", license_name)

def enforce_media_license(media: dict[str, Any]) -> dict[str, Any]:
    decision = check_media_license(media)
    return {
        "allowed": decision.allowed,
        "reason": decision.reason,
        "license": decision.normalized_license,
        "source_url": str(media.get("image_reference_url", "")).strip(),
        "source_type": str(media.get("image_source_type", "ai_generated")).strip().lower(),
    }
