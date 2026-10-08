"""Deterministic local opportunity factory.

This module only computes a shortlist from supplied/local opportunity records.
It never applies, contacts platforms, moves money, or claims revenue.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from .economic_decision import EconomicDecision, decide
from .economic_memory import EconomicObservation, learned_estimate
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
    return current - verified > __import__("datetime").timedelta(days=max_age_days)


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
    max_age_days: int = 7,
    now: datetime | None = None,
) -> list[ShortlistItem]:
    """Return only verified, decision-ready candidates, sorted by score.

    HOLD candidates remain visible only when verification passed; REJECT is
    excluded from the executable shortlist. No external side effects occur.
    """
    unique = deduplicate_records(records)
    history = list(observations)
    candidates: list[ShortlistItem] = []

    for record in unique:
        last_verified_at = record.get("last_verified_at")
        if not isinstance(last_verified_at, str):
            continue
        try:
            stale = is_stale(last_verified_at, max_age_days=max_age_days, now=now)
        except ValueError:
            continue
        if stale:
            continue

        opportunity = Opportunity(
            opportunity_id=record["opportunity_id"],
            expected_pay=float(record.get("expected_pay", 0)),
            acceptance_probability=float(record.get("acceptance_probability", 0)),
            brain_assistance=float(record.get("brain_assistance", 0)),
            time_hours=float(record.get("time_hours", 0)),
            entry_friction=float(record.get("entry_friction", 0)),
            risk=float(record.get("risk", 0)),
        )

        verification = verify_opportunity(
            opportunity_id=record["opportunity_id"],
            eligible_region=bool(record.get("eligible_region", False)),
            remote=bool(record.get("remote", False)),
            upfront_cost_usd=float(record.get("upfront_cost_usd", 0)),
            source_url=record["source_url"],
            last_verified_at=last_verified_at,
            max_age_days=max_age_days,
            now=now,
        )

        result = evaluate(
            [opportunity],
            opportunity_class=str(record.get("opportunity_class", "unknown")),
            eligible=verification.eligible,
            upfront_cost_usd=float(record.get("upfront_cost_usd", 0)),
            source_url=record["source_url"],
            last_verified_at=last_verified_at,
            observations=history,
            max_age_days=max_age_days,
        )

        candidates.append(
            ShortlistItem(
                opportunity_id=opportunity.opportunity_id,
                opportunity_class=str(record.get("opportunity_class", "unknown")),
                source_fingerprint=source_fingerprint(record["source_url"]),
                verification=verification,
                decision=result.decision,
            )
        )

    return sorted(
        (item for item in candidates if item.verification.eligible and item.decision.decision.value != "REJECT"),
        key=lambda item: (-item.decision.score, item.opportunity_id),
    )
