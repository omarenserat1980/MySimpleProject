"""YouTube analytics adapter using the same OAuth refresh-token boundary."""
from __future__ import annotations

from typing import Any
import os
import httpx

from .youtube_api_client import YouTubeApiClient


class YouTubeDataAnalyticsClient:
    def __init__(self) -> None:
        self.api = YouTubeApiClient()
        self.timeout = float(os.getenv("YOUTUBE_API_TIMEOUT_SECONDS", "60"))

    def report(self, *, video_id: str) -> dict[str, Any]:
        token = self.api._access_token()
        with httpx.Client(timeout=self.timeout) as client:
            r = client.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={"part": "statistics,contentDetails,snippet", "id": video_id},
                headers={"Authorization": f"Bearer {token}"},
            )
            r.raise_for_status()
            items = r.json().get("items", [])
        if not items:
            return {"status": "ANALYTICS_NOT_FOUND", "video_id": video_id}
        item = items[0]
        stats = item.get("statistics", {})
        return {
            "status": "ANALYTICS_RECEIVED",
            "video_id": video_id,
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0)),
            "estimated_revenue": None,
            "revenue_verified": False,
        }
