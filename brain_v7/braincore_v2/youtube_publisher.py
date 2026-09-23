"""YouTube publication boundary for the cinematic factory.

A real YouTube API client must be injected by the deployment. No credentials
are stored here. Draft preparation is local; publication requires explicit
authorization and a configured provider.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class YouTubePackage:
    title: str
    description: str
    tags: tuple[str, ...]
    category_id: str = "22"
    privacy: str = "private"


class YouTubeClient(Protocol):
    def upload(self, package: YouTubePackage, video_ref: str) -> dict[str, Any]: ...


def prepare_package(title: str, description: str, tags: list[str] | tuple[str, ...],
                    *, privacy: str = "private") -> dict[str, Any]:
    if not title.strip():
        raise ValueError("title must not be empty")
    if privacy not in {"private", "unlisted", "public"}:
        raise ValueError("invalid privacy")
    package = YouTubePackage(title.strip(), description.strip(), tuple(tags), privacy=privacy)
    return {
        "status": "READY_FOR_YOUTUBE",
        "package": {
            "title": package.title,
            "description": package.description,
            "tags": list(package.tags),
            "category_id": package.category_id,
            "privacy": package.privacy,
        },
        "requires_authorization": True,
        "published": False,
    }


def publish(client: YouTubeClient | None, package: YouTubePackage, video_ref: str,
            *, authorized: bool = False) -> dict[str, Any]:
    if not authorized:
        return {"status": "AUTHORIZATION_REQUIRED", "published": False}
    if client is None:
        return {"status": "YOUTUBE_PROVIDER_NOT_CONFIGURED", "published": False}
    result = client.upload(package, video_ref)
    return {
        "status": "PUBLISHED" if result.get("video_id") else "SUBMISSION_UNVERIFIED",
        "published": bool(result.get("video_id")),
        "provider_result": result,
    }


def snapshot() -> dict[str, Any]:
    return {
        "draft_generation": True,
        "real_youtube_boundary": True,
        "credentials_in_source": False,
        "publication": "explicit_authorization_required",
        "analytics_learning": "ready_for_integration",
    }
