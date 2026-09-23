"""Minimal YouTube Data API client using an OAuth refresh token.

Secrets are read only from environment variables.
"""
from __future__ import annotations
import os
from typing import Any
import httpx

class YouTubeApiClient:
    def __init__(self) -> None:
        self.client_id=os.environ["YOUTUBE_CLIENT_ID"]
        self.client_secret=os.environ["YOUTUBE_CLIENT_SECRET"]
        self.refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"]
        self.token_url="https://oauth2.googleapis.com/token"
        self.upload_url="https://www.googleapis.com/upload/youtube/v3/videos"
    def _access_token(self) -> str:
        with httpx.Client(timeout=60) as c:
            r=c.post(self.token_url,data={"client_id":self.client_id,"client_secret":self.client_secret,"refresh_token":self.refresh_token,"grant_type":"refresh_token"})
            r.raise_for_status()
            return r.json()["access_token"]
    def upload(self, package: Any, video_ref: str) -> dict[str,Any]:
        token=self._access_token()
        path=os.path.abspath(video_ref)
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
        metadata={"snippet":{"title":package.title,"description":package.description,"tags":list(package.tags),"categoryId":package.category_id},"status":{"privacyStatus":package.privacy}}
        headers={"Authorization":f"Bearer {token}","X-Upload-Content-Type":"video/mp4"}
        with open(path,"rb") as f:
            # Simple multipart upload is suitable for modest videos; resumable upload is preferred for large files.
            with httpx.Client(timeout=1800) as c:
                r=c.post(self.upload_url,params={"part":"snippet,status","uploadType":"multipart"},headers=headers,files={"metadata":("metadata.json",__import__("json").dumps(metadata), "application/json"),"media":("video.mp4",f,"video/mp4")})
                r.raise_for_status()
                data=r.json()
        return {"video_id":data.get("id"),"status":"UPLOADED","provider":"youtube_data_api"}
