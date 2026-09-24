"""Minimal YouTube Data API client using an OAuth refresh token.

Secrets are read only from environment variables. OAuth failures are classified
without logging credential values so deployment logs remain safe and actionable.
"""
from __future__ import annotations

import os
from typing import Any

import httpx


class YouTubeOAuthError(RuntimeError):
    def __init__(self, code: str, detail: str, *, status_code: int | None = None) -> None:
        self.code = code
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


class YouTubeApiClient:
    def __init__(self) -> None:
        self.client_id = os.environ["YOUTUBE_CLIENT_ID"].strip()
        self.client_secret = os.environ["YOUTUBE_CLIENT_SECRET"].strip()
        self.refresh_token = os.environ["YOUTUBE_REFRESH_TOKEN"].strip()
        self.token_url = "https://oauth2.googleapis.com/token"
        self.upload_url = "https://www.googleapis.com/upload/youtube/v3/videos"

    def _access_token(self) -> str:
        if not self.client_id or not self.client_secret or not self.refresh_token:
            raise YouTubeOAuthError("OAUTH_CONFIGURATION_INCOMPLETE",
                                    "YouTube OAuth environment variables are incomplete")
        try:
            with httpx.Client(timeout=60) as c:
                r = c.post(self.token_url, data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": self.refresh_token,
                    "grant_type": "refresh_token",
                })
        except httpx.HTTPError as exc:
            raise YouTubeOAuthError("OAUTH_NETWORK_ERROR", "token endpoint request failed") from exc

        if r.status_code >= 400:
            try:
                payload = r.json()
            except ValueError:
                payload = {}
            error = str(payload.get("error", "")).lower()
            if error == "invalid_grant":
                raise YouTubeOAuthError(
                    "OAUTH_REFRESH_TOKEN_INVALID",
                    "refresh token was rejected; it may be revoked, expired, or tied to another OAuth client",
                    status_code=r.status_code,
                )
            if error in {"invalid_client", "unauthorized_client"}:
                raise YouTubeOAuthError(
                    "OAUTH_CLIENT_INVALID",
                    "OAuth client ID/secret is invalid or does not match the refresh token",
                    status_code=r.status_code,
                )
            if error == "invalid_request":
                raise YouTubeOAuthError(
                    "OAUTH_REQUEST_INVALID",
                    "OAuth token request is missing or malformed",
                    status_code=r.status_code,
                )
            raise YouTubeOAuthError(
                "OAUTH_TOKEN_EXCHANGE_FAILED",
                "Google OAuth token exchange was rejected",
                status_code=r.status_code,
            )

        try:
            return str(r.json()["access_token"])
        except (ValueError, KeyError, TypeError) as exc:
            raise YouTubeOAuthError("OAUTH_RESPONSE_INVALID",
                                    "Google returned no usable access token") from exc

    def validate(self) -> dict[str, Any]:
        try:
            self._access_token()
            return {"status": "OAUTH_VALID"}
        except YouTubeOAuthError as exc:
            return {"status": "OAUTH_INVALID", "code": exc.code,
                    "detail": exc.detail, "http_status": exc.status_code}

    def upload(self, package: Any, video_ref: str) -> dict[str, Any]:
        token = self._access_token()
        path = os.path.abspath(video_ref)
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
        metadata = {"snippet": {"title": package.title, "description": package.description,
                                "tags": list(package.tags), "categoryId": package.category_id},
                    "status": {"privacyStatus": package.privacy}}
        headers = {"Authorization": f"Bearer {token}", "X-Upload-Content-Type": "video/mp4"}
        with open(path, "rb") as f:
            with httpx.Client(timeout=1800) as c:
                r = c.post(self.upload_url,
                           params={"part": "snippet,status", "uploadType": "multipart"},
                           headers=headers,
                           files={"metadata": ("metadata.json", __import__("json").dumps(metadata), "application/json"),
                                  "media": ("video.mp4", f, "video/mp4")})
                r.raise_for_status()
                data = r.json()
        return {"video_id": data.get("id"), "status": "UPLOADED", "provider": "youtube_data_api"}
