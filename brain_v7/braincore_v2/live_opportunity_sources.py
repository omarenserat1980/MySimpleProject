"""Live opportunity source registry.

Keeps source policy separate from the search mechanism. A caller may inject
fresh search results; this module normalizes them and rejects stale/unsupported
items. It never submits applications or communicates with clients.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Iterable


@dataclass(frozen=True)
class OpportunitySource:
    name: str
    url: str
    source_type: str
    enabled: bool = True
    requires_fresh_search: bool = True


SOURCES = (
    OpportunitySource("Upwork", "https://www.upwork.com/", "freelance_marketplace"),
    OpportunitySource("Freelancer", "https://www.freelancer.com/", "freelance_marketplace"),
    OpportunitySource("YTJobs", "https://ytjobs.co/", "creator_marketplace"),
    OpportunitySource("Remotive", "https://remotive.com/", "remote_jobs"),
    OpportunitySource("RGB Freelance", "https://rgb.ir/en/freelance", "freelance_marketplace"),
)


def source_registry() -> list[dict[str, Any]]:
    return [asdict(x) for x in SOURCES if x.enabled]


def _age_hours(published_at: str | None) -> float | None:
    if not published_at:
        return None
    try:
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        return max(0.0, (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds() / 3600)
    except ValueError:
        return None


def normalize_search_result(
    result: dict[str, Any],
    *,
    max_age_hours: float = 168.0,
) -> dict[str, Any] | None:
    """Convert a fresh search result into a research candidate.

    Unknown dates are retained as NEEDS_DATE_VERIFICATION rather than being
    treated as current. Unsupported sources are rejected.
    """
    url = str(result.get("url", "")).strip()
    title = str(result.get("title", "")).strip()
    source = str(result.get("source", "")).strip()
    published_at = result.get("publish_date")
    if not url.startswith(("http://", "https://")) or not title or not source:
        return None

    known = {x.name.lower() for x in SOURCES}
    if source.lower() not in known:
        return None

    age = _age_hours(str(published_at)) if published_at else None
    if age is not None and age > max_age_hours:
        return None

    status = "FRESH"
    if age is None:
        status = "NEEDS_DATE_VERIFICATION"

    return {
        "source": source,
        "title": title,
        "url": url,
        "publish_date": published_at,
        "age_hours": round(age, 2) if age is not None else None,
        "evidence_status": status,
        "excerpts": list(result.get("excerpts", [])),
        "requires_manual_verification": True,
    }


def build_research_queue(results: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    seen = set()
    for result in results:
        row = normalize_search_result(result)
        if row and row["url"] not in seen:
            rows.append(row)
            seen.add(row["url"])
    return {
        "candidate_count": len(rows),
        "candidates": rows,
        "execution_enabled": False,
        "submission_requires_user_action": True,
    }
