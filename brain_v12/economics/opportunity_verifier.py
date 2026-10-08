"""Fail-closed verification gate for money-making opportunities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse


@dataclass(frozen=True)
class VerificationResult:
    opportunity_id: str
    eligible: bool
    reasons: tuple[str, ...]


def _has_accepted_region(eligibility: list[str], region: str) -> bool:
    normalized = {item.strip().lower() for item in eligibility}
    return region.strip().lower() in normalized or "remote" in normalized


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
    """Return PASS only when all minimum trust gates are satisfied."""
    reasons: list[str] = []

    if not opportunity_id.strip():
        reasons.append("missing_opportunity_id")

    if not _has_accepted_region(eligibility, region):
        reasons.append("region_not_eligible")

    if upfront_cost_usd < 0:
        reasons.append("invalid_upfront_cost")
    elif upfront_cost_usd > 0:
        reasons.append("upfront_payment_required")

    parsed = urlparse(source_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        reasons.append("invalid_source_url")

    try:
        verified = datetime.fromisoformat(last_verified_at.replace("Z", "+00:00"))
        if verified.tzinfo is None:
            verified = verified.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - verified).total_seconds() / 86400
        if age_days < 0:
            reasons.append("future_verification_timestamp")
        elif age_days > max_age_days:
            reasons.append("stale_source")
    except ValueError:
        reasons.append("invalid_verification_timestamp")

    return VerificationResult(
        opportunity_id=opportunity_id,
        eligible=not reasons,
        reasons=tuple(reasons),
    )
