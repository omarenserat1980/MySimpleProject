"""V10 opportunity intake and execution gate.

Normalizes externally discovered leads into a safe internal queue. External
sources may provide leads, but no financial commitment or payment action is
performed without explicit user authorization.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Iterable

QUEUE_PATH = Path(os.getenv("BRAIN_OPPORTUNITY_QUEUE", "opportunity_queue.json"))
ALLOWED_SERVICES = {
    "product_copy",
    "short_video",
    "ad_creative",
    "listing_package",
}


@dataclass
class Lead:
    source: str
    title: str
    url: str
    service: str
    offered_jod: float | None = None
    deadline: str | None = None
    description: str = ""

    @property
    def lead_id(self) -> str:
        raw = "|".join([self.source, self.title, self.url, self.service])
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["lead_id"] = self.lead_id
        return data


def normalize_lead(raw: dict[str, Any]) -> Lead | None:
    service = str(raw.get("service", "")).strip()
    title = str(raw.get("title", "")).strip()
    url = str(raw.get("url", "")).strip()
    source = str(raw.get("source", "")).strip()
    if not title or not url or not source or service not in ALLOWED_SERVICES:
        return None
    offered = raw.get("offered_jod")
    try:
        offered = float(offered) if offered is not None else None
    except (TypeError, ValueError):
        offered = None
    return Lead(
        source=source,
        title=title,
        url=url,
        service=service,
        offered_jod=offered,
        deadline=str(raw.get("deadline")) if raw.get("deadline") else None,
        description=str(raw.get("description", "")),
    )


def ingest(raw_leads: Iterable[dict[str, Any]]) -> dict[str, Any]:
    leads = []
    seen = set()
    for raw in raw_leads:
        lead = normalize_lead(raw)
        if lead and lead.lead_id not in seen:
            leads.append(lead.to_dict())
            seen.add(lead.lead_id)
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_PATH.write_text(json.dumps(leads, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "QUEUED", "count": len(leads), "leads": leads}


def list_leads() -> list[dict[str, Any]]:
    try:
        data = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def mark_lead(lead_id: str, status: str, note: str = "") -> dict[str, Any]:
    data = list_leads()
    for lead in data:
        if lead.get("lead_id") == lead_id:
            lead["status"] = str(status)
            lead["updated_at"] = time.time()
            if note:
                lead["note"] = note
    QUEUE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return next((x for x in data if x.get("lead_id") == lead_id), {"status": "NOT_FOUND"})
