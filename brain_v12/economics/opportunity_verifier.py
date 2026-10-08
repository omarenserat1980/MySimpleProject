"""Fail-closed opportunity verification with confidence and audit metadata."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from urllib.parse import urlparse


@dataclass(frozen=True)
class VerificationResult:
    opportunity_id: str
    eligible: bool
    reasons: tuple[str, ...]
    confidence: float
    source_fingerprint: str


def _has_accepted_region(eligibility: list[str], region: str) -> bool:
    normalized = {item.strip().lower() for item in eligibility}
    return region.strip().lower() in normalized or "remote" in normalized


def _fingerprint(source_url: str) -> str:
    return sha256(source_url.strip().lower().encode("utf-8")).hexdigest()


def verify_opportunity(
    *,
    opportunity_id: str,
    eligibility: list[str],
    upfront_cost_usd: float,
    source_url: str,
    last_verified_at: str,
    region: str = "Jordan",
    max_age_days: int = 30,
) -> VerificationResult:
    """Return PASS only when every trust gate is satisfied."""
    reasons: list[str] = []
    checks = 0
    passed = 0

    def check(condition: bool, failure: str) -> None:
        nonlocal checks, passed
        checks += 1
        if condition:
            passed += 1
        else:
            reasons.append(failure)

    check(bool(opportunity_id.strip()), "missing_opportunity_id")
    check(_has_accepted_region(eligibility, region), "region_not_eligible")
    check(upfront_cost_usd >= 0, "invalid_upfront_cost")
    check(upfront_cost_usd == 0, "upfront_payment_required")

    parsed = urlparse(source_url)
    check(
        parsed.scheme in {"http", "https"} and bool(parsed.netloc),
        "invalid_source_url",
    )

    timestamp_valid = False
    try:
        verified = datetime.fromisoformat(last_verified_at.replace("Z", "+00:00"))
        if verified.tzinfo is None:
            verified = verified.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - verified).total_seconds() / 86400
        if age_days < 0:
            reasons.append("future_verification_timestamp")
        elif age_days > max_age_days:
            reasons.append("stale_source")
        else:
            timestamp_valid = True
    except ValueError:
        reasons.append("invalid_verification_timestamp")

    checks += 1
    if timestamp_valid:
        passed += 1

    confidence = passed / checks if checks else 0.0
    eligible = not reasons and confidence == 1.0

    return VerificationResult(
        opportunity_id=opportunity_id,
        eligible=eligible,
        reasons=tuple(reasons),
        confidence=confidence,
        source_fingerprint=_fingerprint(source_url),
    )
