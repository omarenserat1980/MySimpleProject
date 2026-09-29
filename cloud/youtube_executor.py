"""Cloud-only YouTube publication executor.

Credentials are read exclusively from cloud environment/secret storage.
No phone, Termux, or local desktop integration exists here.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def publish_video(*, video_path: str, title: str, description: str,
                  tags: list[str], privacy: str = "private") -> dict[str, Any]:
    if os.getenv("FACTORY_ALLOW_YOUTUBE_PUBLISH", "0") != "1":
        return {"published": False, "status": "PUBLISH_DISABLED"}
    if not Path(video_path).is_file():
        return {"published": False, "status": "VIDEO_NOT_FOUND"}
    required = ["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"]
    if not all(os.getenv(k, "").strip() for k in required):
        return {"published": False, "status": "YOUTUBE_CLOUD_CREDENTIALS_NOT_CONFIGURED"}

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        creds = Credentials(
            token=None,
            refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.environ["YOUTUBE_CLIENT_ID"],
            client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
            scopes=["https://www.googleapis.com/auth/youtube.upload"],
        )
        youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
        body = {"snippet": {
            "title": title.strip(),
            "description": description.strip(),
            "tags": tags[:30],
            "categoryId": "22",
        }, "status": {"privacyStatus": privacy}}
        media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        response = None
        while response is None:
            _, response = request.next_chunk()
        video_id = response.get("id") if isinstance(response, dict) else None
        return {"published": bool(video_id), "status": "PUBLISHED" if video_id else "SUBMISSION_UNVERIFIED",
                "video_id": video_id}
    except Exception as exc:
        return {"published": False, "status": "YOUTUBE_UPLOAD_ERROR",
                "error": f"{type(exc).__name__}: {exc}"}
