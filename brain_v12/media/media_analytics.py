"""Media performance metrics used for learning, not automatic publication."""
from __future__ import annotations

def summarize(items: list[dict]) -> dict:
    if not items:
        return {"sample_size": 0, "engagement_rate": 0.0}
    impressions = sum(float(x.get("impressions", 0)) for x in items)
    engagements = sum(float(x.get("engagements", 0)) for x in items)
    rate = 100.0 * engagements / impressions if impressions else 0.0
    return {"sample_size": len(items), "impressions": impressions, "engagements": engagements,
            "engagement_rate": round(rate, 4)}
