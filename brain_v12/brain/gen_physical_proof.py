"""GEN physical-evidence gate for Brain V12.

Offline-only evaluator. It does not discover devices, open network connections,
verify cryptographic signatures, or prove physical presence by itself. A trusted
integration must supply independently verified verification results.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Mapping
import hashlib
import json


STATUSES = frozenset({
    "NOT_PROVEN", "SIMULATED", "CLAIMED", "CONNECTED_UNVERIFIED",
    "CHALLENGE_FAILED", "PHYSICALLY_ATTESTED", "EXPIRED",
})
REAL_SUBJECT_TYPES = frozenset({"ASIC_DEVICE", "HOSTED_ASIC"})
TRUSTED_SOURCE_TYPES = frozenset({"DEVICE_ATTESTATION", "PROVIDER_API"})


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def canonical_digest(payload: Mapping[str, Any]) -> str:
    """Return an integrity digest; this does not establish truth or provenance."""
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class GENProofResult:
    status: str
    accepted: bool
    blocked_reasons: tuple[str, ...]
    evidence_digest: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["blocked_reasons"] = list(self.blocked_reasons)
        return result


def evaluate_physical_proof(
    evidence: Mapping[str, Any] | None,
    *,
    now: datetime | None = None,
) -> GENProofResult:
    """Fail-closed evaluation of evidence metadata supplied by a trusted verifier.

    This function is not itself an attestation verifier. The fields
    identity_verified, signature_verified, challenge_fresh, network_verified,
    and device_diagnostic_passed must be produced by independently trusted
    verification code, not copied from an untrusted caller or device response.
    """
    if not isinstance(evidence, Mapping):
        return GENProofResult("NOT_PROVEN", False, ("EVIDENCE_MISSING",))

    source = evidence.get("source_type")
    if source == "SIMULATOR":
        return GENProofResult("SIMULATED", False, ("SIMULATOR_CANNOT_PROVE_PHYSICAL_DEVICE",),
                              canonical_digest(dict(evidence)))
    if source not in TRUSTED_SOURCE_TYPES:
        status = "CONNECTED_UNVERIFIED" if evidence.get("network_connection_verified") is True else "CLAIMED"
        return GENProofResult(status, False, ("INDEPENDENT_TRUSTED_ATTESTATION_REQUIRED",),
                              canonical_digest(dict(evidence)))

    reasons: list[str] = []
    subject_type = evidence.get("subject_type")
    if subject_type not in REAL_SUBJECT_TYPES:
        reasons.append("INVALID_OR_MISSING_SUBJECT_TYPE")
    for key in ("subject_id", "evidence_id", "operation", "verifier_version"):
        if not isinstance(evidence.get(key), str) or not evidence[key].strip():
            reasons.append(f"{key.upper()}_REQUIRED")

    observed = _parse_time(evidence.get("observed_at_utc"))
    expires = _parse_time(evidence.get("expires_at_utc"))
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    current = current.astimezone(timezone.utc)
    if observed is None or expires is None:
        reasons.append("VALID_UTC_TIMESTAMPS_REQUIRED")
    else:
        if observed > current:
            reasons.append("OBSERVATION_FROM_FUTURE")
        if expires <= current:
            return GENProofResult("EXPIRED", False, ("EVIDENCE_EXPIRED",),
                                  canonical_digest(dict(evidence)))
        if expires <= observed:
            reasons.append("INVALID_EVIDENCE_VALIDITY_WINDOW")

    checks = {
        "identity_verified": "INDEPENDENT_IDENTITY_VERIFICATION_REQUIRED",
        "signature_verified": "VALID_TRUSTED_SIGNATURE_REQUIRED",
        "challenge_fresh": "FRESH_CHALLENGE_REQUIRED",
        "network_connection_verified": "LIVE_NETWORK_CONNECTION_REQUIRED",
        "physical_presence_verified": "INDEPENDENT_PHYSICAL_PRESENCE_EVIDENCE_REQUIRED",
        "device_diagnostic_passed": "REAL_DEVICE_DIAGNOSTIC_REQUIRED",
    }
    for key, reason in checks.items():
        if evidence.get(key) is not True:
            reasons.append(reason)

    if not isinstance(evidence.get("challenge_nonce_digest"), str) or not evidence["challenge_nonce_digest"].strip():
        reasons.append("CHALLENGE_NONCE_BINDING_REQUIRED")
    if not isinstance(evidence.get("result_digest"), str) or not evidence["result_digest"].strip():
        reasons.append("DEVICE_RESULT_DIGEST_REQUIRED")
    if reasons:
        status = "CHALLENGE_FAILED" if any("CHALLENGE" in reason or "SIGNATURE" in reason for reason in reasons) else "NOT_PROVEN"
        return GENProofResult(status, False, tuple(dict.fromkeys(reasons)), canonical_digest(dict(evidence)))

    # Fail closed until a cryptographic verifier is implemented and wired in.
    # Evidence fields (including booleans and digests) are caller-controlled data;
    # accepting them here would let forged JSON claim a physical device.
    return GENProofResult(
        "NOT_PROVEN",
        False,
        ("TRUSTED_CRYPTOGRAPHIC_VERIFIER_NOT_IMPLEMENTED",),
        canonical_digest(dict(evidence)),
    )


__all__ = ["GENProofResult", "canonical_digest", "evaluate_physical_proof", "STATUSES"]
