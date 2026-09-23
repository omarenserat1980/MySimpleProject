"""Revenue opportunity engine for the Electronic Brain.

Ranks candidate digital services by a transparent, deterministic score.
This is a decision aid, not a guarantee of income.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import os
import time
from pathlib import Path
from typing import Any

LEDGER_PATH = Path(os.getenv("BRAIN_REVENUE_LEDGER", "revenue_ledger.json"))


@dataclass
class Opportunity:
    name: str
    service: str
    expected_jod: float
    effort_hours: float
    demand: float
    proofability: float
    platform_friction: float

    @property
    def hourly_value(self) -> float:
        return self.expected_jod / max(self.effort_hours, 0.25)

    @property
    def score(self) -> float:
        # Higher demand/proofability and lower friction/effort are preferred.
        raw = (
            self.hourly_value * 0.45
            + self.demand * 20.0 * 0.25
            + self.proofability * 20.0 * 0.20
            + (1.0 - self.platform_friction) * 20.0 * 0.10
        )
        return round(raw, 2)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["hourly_value"] = round(self.hourly_value, 2)
        data["score"] = self.score
        return data


DEFAULT_OPPORTUNITIES = [
    Opportunity("Arabic product ad copy", "product_copy", 10, 0.5, 0.80, 0.95, 0.10),
    Opportunity("Short product promo video", "short_video", 25, 1.5, 0.85, 0.90, 0.15),
    Opportunity("Product image/ad creative", "ad_creative", 20, 1.0, 0.82, 0.90, 0.12),
    Opportunity("Arabic product listing package", "listing_package", 35, 2.0, 0.78, 0.95, 0.12),
]


def rank_opportunities(items: list[Opportunity] | None = None) -> list[dict[str, Any]]:
    candidates = items or DEFAULT_OPPORTUNITIES
    return [x.to_dict() for x in sorted(candidates, key=lambda x: x.score, reverse=True)]


def record_outcome(name: str, status: str, amount_jod: float = 0.0, note: str = "") -> dict[str, Any]:
    entry = {
        "timestamp": time.time(),
        "name": str(name),
        "status": str(status),
        "amount_jod": float(amount_jod),
        "note": str(note),
    }
    try:
        data = json.loads(LEDGER_PATH.read_text(encoding="utf-8")) if LEDGER_PATH.is_file() else []
        if not isinstance(data, list):
            data = []
        data.append(entry)
        LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
        LEDGER_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return entry
