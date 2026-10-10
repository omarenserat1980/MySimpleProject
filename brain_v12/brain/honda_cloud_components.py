"""Policy-first cloud components for a Honda vehicle profile.

Planning/validation only: this module does not connect to a vehicle, send commands,
provision cloud resources, or install firmware. It keeps the integration read-only
and defaults to zero-cost, disabled cloud synchronization.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Any


SUPPORTED_PROFILES = {"HONDA_NBOX", "HONDA_ENP1", "HONDA_UNVERIFIED"}
COMPONENTS = (
    "vehicle_profile_registry",
    "firmware_metadata_verifier",
    "evidence_vault",
    "health_alert_relay",
    "cloud_executor",
)


@dataclass(frozen=True)
class HondaCloudPolicy:
    """Explicit gates for cloud use; all potentially risky features default off."""

    cloud_sync_enabled: bool = False
    allow_paid_resources: bool = False
    allow_remote_vehicle_commands: bool = False
    allow_firmware_install: bool = False
    max_cost_usd: float = 0.0

    def __post_init__(self) -> None:
        if self.max_cost_usd < 0:
            raise ValueError("max_cost_usd cannot be negative")
        if not self.allow_paid_resources and self.max_cost_usd != 0:
            raise ValueError("nonzero budget requires explicit paid-resource approval")
        if self.allow_remote_vehicle_commands:
            raise ValueError("remote vehicle commands are not supported by this integration")
        if self.allow_firmware_install:
            raise ValueError("automatic firmware installation is not supported")


@dataclass(frozen=True)
class HondaVehicleProfile:
    """Minimum metadata only; never store a raw VIN in this profile."""

    profile_id: str
    model_code: str = "HONDA_UNVERIFIED"
    model_year: int | None = None
    head_unit: str | None = None
    vin_sha256: str | None = None
    verified: bool = False

    def __post_init__(self) -> None:
        if not self.profile_id.strip():
            raise ValueError("profile_id is required")
        if self.model_code not in SUPPORTED_PROFILES:
            raise ValueError("unsupported or unnormalized Honda model code")
        if self.model_year is not None and not 1990 <= self.model_year <= 2100:
            raise ValueError("model_year is outside the accepted range")
        if self.vin_sha256 and (
            len(self.vin_sha256) != 64
            or any(ch not in "0123456789abcdef" for ch in self.vin_sha256.lower())
        ):
            raise ValueError("vin_sha256 must be a SHA-256 hex digest")


def fingerprint_vin(vin: str) -> str:
    """Return a one-way SHA-256 fingerprint; callers should not upload the raw VIN."""
    normalized = "".join(vin.split()).upper()
    if len(normalized) != 17 or any(ch in normalized for ch in "IOQ"):
        raise ValueError("VIN must be a valid 17-character identifier")
    return sha256(normalized.encode("ascii")).hexdigest()


def evidence_digest(payload: dict[str, Any]) -> str:
    """Canonical digest for a read-only diagnostic or firmware metadata report."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(canonical.encode("utf-8")).hexdigest()


def plan_honda_cloud_components(
    profile: HondaVehicleProfile, policy: HondaCloudPolicy
) -> dict[str, Any]:
    """Return a safe deployment plan without provisioning or making network calls."""
    cloud_enabled = policy.cloud_sync_enabled
    verified = profile.verified and profile.model_code != "HONDA_UNVERIFIED"
    states = {
        "vehicle_profile_registry": "READY_LOCAL" if verified else "WAITING_FOR_VEHICLE_VERIFICATION",
        "firmware_metadata_verifier": "READ_ONLY_READY",
        "evidence_vault": "ENABLED_BY_POLICY" if cloud_enabled else "LOCAL_ONLY",
        "health_alert_relay": "ENABLED_BY_POLICY" if cloud_enabled else "DISABLED",
        "cloud_executor": "ELIGIBLE_FREE_TIER_ONLY" if cloud_enabled else "DISABLED",
    }
    return {
        "profile": asdict(profile),
        "policy": asdict(policy),
        "components": states,
        "cost_ceiling_usd": policy.max_cost_usd if policy.allow_paid_resources else 0.0,
        "safety": {
            "remote_vehicle_commands": False,
            "automatic_firmware_install": False,
            "raw_vin_upload": False,
            "cloud_provisioning_performed": False,
        },
        "next_gate": (
            "VERIFY_MODEL_AND_HEAD_UNIT"
            if not verified
            else "EXPLICITLY_ENABLE_CLOUD_SYNC"
            if not cloud_enabled
            else "ENROLL_AUTHENTICATED_EVIDENCE_DESTINATION"
        ),
    }
