"""Deterministic local opportunity factory.

No applications, external writes, money movement, or revenue claims.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from .economic_decision import EconomicDecision
from .economic_memory import EconomicObservation
from .economic_orchestrator import evaluate
from .opportunity_engine import Opportunity
from .opportunity_verifier import VerificationResult, verify_opportunity
from .source_identity import source_fingerprint


@dataclass(frozen=True)
class ShortlistItem:
    opportunity_id: str
    opportunity_class: str
    source_fingerprint: str
    verification: VerificationResult
    decision: EconomicDecision


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def is_stale(last_verified_at: str, *, max_age_days: int, now: datetime | None = None) -> bool:
    if max_age_days < 0:
        raise ValueError("max_age_days cannot be negative")
    verified = _parse_timestamp(last_verified_at)
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return (current - verified).total_seconds() > max_age_days * 86400


def deduplicate_records(records: Iterable[dict]) -> list[dict]:
    seen_ids: set[str] = set()
    seen_sources: set[str] = set()
    result: list[dict] = []

    for record in records:
        opportunity_id = str(record.get("opportunity_id", "")).strip()
        source_url = str(record.get("source_url", "")).strip()
        if not opportunity_id or not source_url:
            continue
        try:
            fingerprint = source_fingerprint(source_url)
        except ValueError:
            continue
        if opportunity_id in seen_ids or fingerprint in seen_sources:
            continue
        seen_ids.add(opportunity_id)
        seen_sources.add(fingerprint)
        result.append(record)
    return result


def build_shortlist(
    records: Iterable[dict],
    *,
    observations: Iterable[EconomicObservation] = (),
    max_age_days: int = 30,
    now: datetime | None = None,
) -> list[ShortlistItem]:
    """Build a verified, explainable shortlist through one orchestration path."""
    history = list(observations)
    candidates: list[ShortlistItem] = []

    for record in deduplicate_records(records):
        last_verified_at = record.get("last_verified_at")
        if not isinstance(last_verified_at, str):
            continue
        try:
            if is_stale(last_verified_at, max_age_days=max_age_days, now=now):
                continue

            opportunity = Opportunity(
                opportunity_id=str(record["opportunity_id"]),
                expected_pay=float(record.get("expected_pay", 0)),
                acceptance_probability=float(record.get("acceptance_probability", 0)),
                brain_assistance=float(record.get("brain_assistance", 0)),
                time_hours=float(record.get("time_hours", 0)),
                entry_friction=float(record.get("entry_friction", 0)),
                risk=float(record.get("risk", 0)),
            )

            eligibility = list(record.get("eligibility", []))
            if not eligibility:
                if record.get("eligible_region"):
                    eligibility.append("Jordan")
                if record.get("remote"):
                    eligibility.append("remote")

            result = evaluate(
                opportunity,
                opportunity_class=str(record.get("opportunity_class", "unknown")),
                eligibility=eligibility,
                upfront_cost_usd=float(record.get("upfront_cost_usd", 0)),
                source_url=str(record["source_url"]),
                last_verified_at=last_verified_at,
                observations=history,
            )
        except (KeyError, TypeError, ValueError):
            continue

        candidates.append(
            ShortlistItem(
                opportunity_id=opportunity.opportunity_id,
                opportunity_class=str(record.get("opportunity_class", "unknown")),
                source_fingerprint=source_fingerprint(str(record["source_url"])),
                verification=result.verification,
                decision=result.decision,
            )
        )

    return sorted(
        (item for item in candidates if item.verification.eligible),
        key=lambda item: (-item.decision.score, item.opportunity_id),
    )
