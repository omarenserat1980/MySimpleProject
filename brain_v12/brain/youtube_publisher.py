"""Authorization-gated YouTube publishing coordinator for V12.

Prepares cinematic releases locally and uploads only through an explicitly
invoked, configured Google OAuth credential. Publication is verified by reading
the uploaded video back from YouTube; Brain never logs OAuth secrets.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import os
import subprocess
from typing import Any, Callable

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


class YouTubePublisher:
    def __init__(self, store, credentials_provider: Callable[[], Any] | None = None):
        self.store = store
        self.credentials_provider = credentials_provider

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

    def validate_release(self, title: str, media_path: str, description: str = "",
                         tags: list[str] | None = None) -> dict[str, Any]:
        path = Path(media_path.strip()) if media_path.strip() else None
        checks = {
            "title": bool(title.strip()),
            "media_path": bool(media_path.strip()) and bool(path and path.is_file()),
            "description": len(description.strip()) <= 5000,
            "tags": len(tags or []) <= 30,
        }
        if path and path.is_file():
            try:
                probe = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries",
                     "format=duration", "-of", "default=nw=1:nk=1", str(path)],
                    capture_output=True, text=True, timeout=30, check=False,
                )
                checks["ffprobe"] = probe.returncode == 0 and float(probe.stdout.strip() or "0") > 0
            except (OSError, ValueError, subprocess.TimeoutExpired):
                checks["ffprobe"] = False
        else:
            checks["ffprobe"] = False
        ok = all(checks.values())
        return {"ok": ok, "checks": checks, "status": "VALID" if ok else "INVALID"}

    def authorize(self, release_id: str) -> dict[str, Any]:
        self.store.event("YOUTUBE_RELEASE_AUTHORIZATION_REQUESTED",
                         {"release_id": release_id, "status": "HUMAN_AUTHORIZATION_REQUIRED"})
        return {"ok": False, "release_id": release_id,
                "status": "HUMAN_AUTHORIZATION_REQUIRED",
                "published": False}

    def publish_cinematic_release(
        self,
        title: str,
        description: str = "",
        media_path: str = "",
        tags: list[str] | None = None,
        privacy: str = "private",
        category_id: str = "22",
        thumbnail_path: str = "",
    ) -> dict[str, Any]:
        validation = self.validate_release(title, media_path, description, tags)
        if not validation["ok"]:
            return {"ok": False, "status": "VALIDATION_FAILED", "validation": validation}

        if privacy not in {"private", "unlisted", "public"}:
            return {"ok": False, "status": "INVALID_PRIVACY"}

        if not self.credentials_provider:
            return {"ok": False, "status": "YOUTUBE_OAUTH_PROVIDER_NOT_CONNECTED"}

        credentials = self.credentials_provider()
        if credentials is None:
            return {
                "ok": False,
                "status": "YOUTUBE_AUTHORIZATION_REQUIRED",
                "authorization_required": True,
            }

        release_id = self._id(title.strip(), media_path)
        started = datetime.now(timezone.utc).isoformat()
        self.store.event("YOUTUBE_UPLOAD_STARTED", {
            "release_id": release_id,
            "title": title.strip(),
            "privacy": privacy,
            "started_at": started,
        })

        try:
            youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
            body = {
                "snippet": {
                    "title": title.strip(),
                    "description": description.strip(),
                    "tags": [str(x).strip() for x in (tags or []) if str(x).strip()][:30],
                    "categoryId": str(category_id),
                },
                "status": {
                    "privacyStatus": privacy,
                    "selfDeclaredMadeForKids": False,
                },
            }
            media = MediaFileUpload(media_path, resumable=True)
            response = youtube.videos().insert(
                part="snippet,status", body=body, media_body=media
            ).execute()
            video_id = str(response.get("id", "")).strip()
            if not video_id:
                raise RuntimeError("YouTube upload returned no video id")

            thumbnail_result = None
            if thumbnail_path:
                thumbnail = Path(thumbnail_path)
                if not thumbnail.is_file():
                    raise ValueError("thumbnail_path does not exist")
                thumbnail_result = youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(str(thumbnail), mimetype="image/jpeg"),
                ).execute()

            verified = youtube.videos().list(
                part="snippet,status", id=video_id
            ).execute()
            items = verified.get("items") or []
            if not items:
                raise RuntimeError("YouTube verification returned no video")

            item = items[0]
            verified_status = item.get("status", {}).get("privacyStatus")
            published_url = f"https://www.youtube.com/watch?v={video_id}"
            evidence = {
                "video_id": video_id,
                "privacy_status": verified_status,
                "title": item.get("snippet", {}).get("title"),
                "verified_at": datetime.now(timezone.utc).isoformat(),
            }
            result = {
                "ok": True,
                "status": "PUBLISHED_VERIFIED",
                "release_id": release_id,
                "video_id": video_id,
                "published_url": published_url,
                "privacy": verified_status,
                "thumbnail_set": bool(thumbnail_result),
                "evidence": evidence,
            }
            self.store.event("YOUTUBE_RELEASE_PUBLISHED_VERIFIED", result)
            return result
        except Exception as exc:
            error = str(exc)[:500]
            self.store.event("YOUTUBE_UPLOAD_FAILED", {
                "release_id": release_id,
                "status": "UPLOAD_FAILED",
                "error": error,
                "failed_at": datetime.now(timezone.utc).isoformat(),
            })
            return {"ok": False, "status": "UPLOAD_FAILED", "release_id": release_id, "error": error}

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
        return {"ok": True, "external_publishing": "OAUTH_VERIFIED_UPLOAD",
                "credentials_stored_by_brain": False,
                "money_movement": False,
                "supported_privacy": ["private", "unlisted", "public"],
                "verified_publications": 0}
