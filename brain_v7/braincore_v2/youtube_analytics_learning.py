"""Provider-neutral YouTube analytics learning boundary."""
from __future__ import annotations

from typing import Any, Protocol


class YouTubeAnalyticsClient(Protocol):
    def get_video_metrics(self, *, video_id: str) -> dict[str, Any]: ...


def normalize_metrics(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "video_id": raw.get("video_id"),
        "views": raw.get("views"),
        "watch_time_minutes": raw.get("watch_time_minutes"),
        "average_view_duration_seconds": raw.get("average_view_duration_seconds"),
        "average_view_percentage": raw.get("average_view_percentage"),
        "impressions": raw.get("impressions"),
        "click_through_rate": raw.get("click_through_rate"),
        "likes": raw.get("likes"),
        "comments": raw.get("comments"),
        "subscribers_gained": raw.get("subscribers_gained"),
        "estimated_revenue": raw.get("estimated_revenue"),
        "revenue_currency": raw.get("revenue_currency"),
        "revenue_verified": bool(raw.get("revenue_verified", False)),
    }


def learn(metrics: dict[str, Any]) -> dict[str, Any]:
    m = normalize_metrics(metrics)
    actions = []
    if isinstance(m.get("click_through_rate"), (int, float)) and m["click_through_rate"] < 0.04:
        actions.append("test stronger thumbnail/title packaging")
    if isinstance(m.get("average_view_percentage"), (int, float)) and m["average_view_percentage"] < 0.35:
        actions.append("strengthen first 30 seconds and remove slow sections")
    if isinstance(m.get("comments"), int) and m["comments"] == 0:
        actions.append("add a clear audience question or call-to-action")
    return {
        "metrics": m,
        "next_actions": actions,
        "verified_revenue_jod": 0.0,
        "revenue_status": "VERIFIED_ONLY" if m["revenue_verified"] else "NOT_VERIFIED",
    }


def snapshot() -> dict[str, Any]:
    return {
        "analytics_ingestion": True,
        "retention_learning": True,
        "thumbnail_learning": True,
        "revenue_verification": True,
        "provider_neutral": True,
    }
