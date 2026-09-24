"""Authorization-gated YouTube publishing coordinator for V12.

Prepares cinematic releases locally and records auditable release state. It never
stores OAuth secrets, uploads videos, or publishes externally without explicit
authorization and a configured external publishing adapter.
"""
from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any


class YouTubePublisher:
    def __init__(self, store):
        self.store = store

    @staticmethod
    def _id(title: str, media_path: str) -> str:
        raw = f"{title}|{media_path}".encode()
        return "YT-" + sha256(raw).hexdigest()[:16]

    def prepare_cinematic_release(self, title: str, description: str = "",
                                  media_path: str = "", tags: list[str] | None = None,
                                  privacy: str = "private") -> dict[str, Any]:
        if not title.strip():
            raise ValueError("title is required")
        if privacy not in {"private", "unlisted", "public"}:
            raise ValueError("invalid privacy")
        release_id = self._id(title.strip(), media_path)
        now = datetime.now(timezone.utc).isoformat()
        package = {
            "release_id": release_id,
            "title": title.strip(),
            "description": description.strip(),
            "media_path": media_path,
            "tags": [str(x).strip() for x in (tags or []) if str(x).strip()][:30],
            "privacy": privacy,
            "status": "READY_FOR_AUTHORIZATION",
            "authorization_required": True,
            "published": False,
            "published_url": None,
            "prepared_at": now,
        }
        self.store.event("YOUTUBE_CINEMATIC_RELEASE_PREPARED", package)
        return package

    def authorize(self, release_id: str) -> dict[str, Any]:
        self.store.event("YOUTUBE_RELEASE_AUTHORIZATION_REQUESTED",
                         {"release_id": release_id, "status": "HUMAN_AUTHORIZATION_REQUIRED"})
        return {"ok": False, "release_id": release_id,
                "status": "HUMAN_AUTHORIZATION_REQUIRED",
                "published": False}

    def record_published(self, release_id: str, published_url: str,
                         evidence: str) -> dict[str, Any]:
        if not published_url.startswith(("https://www.youtube.com/", "https://youtu.be/")):
            raise ValueError("published_url must be a YouTube URL")
        if not evidence.strip():
            raise ValueError("publication evidence is required")
        result = {"release_id": release_id, "status": "PUBLISHED",
                  "published": True, "published_url": published_url,
                  "evidence": evidence[:1000],
                  "published_at": datetime.now(timezone.utc).isoformat()}
        self.store.event("YOUTUBE_RELEASE_PUBLISHED_VERIFIED", result)
        return result

    def snapshot(self) -> dict[str, Any]:
        return {"ok": True, "external_publishing": "AUTHORIZATION_REQUIRED",
                "credentials_stored_by_brain": False,
                "money_movement": False}
