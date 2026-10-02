"""Freshness-aware public market snapshot utilities.

The engine only accepts explicit source timestamps and never treats a missing
timestamp as live data.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class MarketSnapshot:
    asset: str
    hashprice_usd_per_th_day: float
    observed_at: str
    source: str
    btc_price_usd: float | None = None
    network_hashrate_eh: float | None = None
    difficulty: float | None = None
    evidence_urls: tuple[str, ...] = ()

    def observed_datetime(self) -> datetime:
        value=self.observed_at.replace("Z","+00:00")
        dt=datetime.fromisoformat(value)
        if dt.tzinfo is None:
            raise ValueError("observed_at must include timezone")
        return dt.astimezone(timezone.utc)

    def age_hours(self, now: datetime | None = None) -> float:
        now=(now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        return max(0.0, (now-self.observed_datetime()).total_seconds()/3600.0)

    def freshness(self, max_age_hours: float = 24.0,
                  now: datetime | None = None) -> str:
        if max_age_hours <= 0:
            raise ValueError("max_age_hours must be > 0")
        return "FRESH" if self.age_hours(now) <= max_age_hours else "STALE"

    def validate(self, max_age_hours: float = 24.0,
                 now: datetime | None = None) -> dict[str, Any]:
        if not self.asset.strip() or not self.source.strip():
            raise ValueError("asset and source are required")
        if self.hashprice_usd_per_th_day <= 0:
            raise ValueError("hashprice must be > 0")
        freshness=self.freshness(max_age_hours, now)
        return {
            "valid": True,
            "freshness": freshness,
            "age_hours": round(self.age_hours(now), 3),
            "observed_at": self.observed_at,
            "source": self.source,
            "evidence_urls": list(self.evidence_urls),
        }
