"""Controlled YouTube operations for the Electronic Brain."""
from __future__ import annotations
import os
from typing import Any
import httpx
from .youtube_api_client import YouTubeApiClient

class YouTubeChannelControl:
    def __init__(self) -> None:
        self.api = YouTubeApiClient()
        self.base = "https://www.googleapis.com/youtube/v3"
        self.timeout = float(os.getenv("YOUTUBE_API_TIMEOUT_SECONDS", "60"))

    def _headers(self):
        return {"Authorization": "Bearer " + self.api._access_token()}

    def channel(self):
        with httpx.Client(timeout=self.timeout) as c:
            r=c.get(self.base+"/channels", params={"part":"snippet,statistics,contentDetails,status","mine":"true"}, headers=self._headers())
            r.raise_for_status()
            items=r.json().get("items",[])
        if not items: return {"status":"CHANNEL_NOT_FOUND"}
        x=items[0]
        return {"status":"CHANNEL_RECEIVED","channel_id":x.get("id"),"title":x.get("snippet",{}).get("title"),"statistics":x.get("statistics",{}),"uploads_playlist_id":x.get("contentDetails",{}).get("relatedPlaylists",{}).get("uploads")}

    def videos(self, limit=25):
        ch=self.channel()
        pid=ch.get("uploads_playlist_id")
        if not pid: return {"status":"UPLOADS_PLAYLIST_NOT_FOUND","items":[]}
        with httpx.Client(timeout=self.timeout) as c:
            r=c.get(self.base+"/playlistItems",params={"part":"snippet,contentDetails,status","playlistId":pid,"maxResults":max(1,min(50,int(limit)))},headers=self._headers())
            r.raise_for_status()
            return {"status":"VIDEOS_RECEIVED","items":r.json().get("items",[])}

    def update_video(self, video_id, title=None, description=None, tags=None, privacy=None):
        with httpx.Client(timeout=self.timeout) as c:
            old=c.get(self.base+"/videos",params={"part":"snippet,status","id":video_id},headers=self._headers())
            old.raise_for_status()
            items=old.json().get("items",[])
            if not items: return {"status":"VIDEO_NOT_FOUND","video_id":video_id}
            x=items[0]; snippet=dict(x.get("snippet",{})); status=dict(x.get("status",{}))
            if title is not None: snippet["title"]=title
            if description is not None: snippet["description"]=description
            if tags is not None: snippet["tags"]=list(tags)
            if privacy is not None:
                if privacy not in {"private","public","unlisted"}: raise ValueError("invalid privacy")
                status["privacyStatus"]=privacy
            r=c.put(self.base+"/videos",params={"part":"snippet,status"},headers={**self._headers(),"Content-Type":"application/json"},json={"id":video_id,"snippet":snippet,"status":status})
            r.raise_for_status()
            return {"status":"VIDEO_UPDATED","video_id":r.json().get("id",video_id)}

    def policy(self, action):
        action=str(action).upper()
        gated={"DELETE_VIDEO","CHANGE_CHANNEL_SETTINGS","CHANGE_BRANDING","DELETE_PLAYLIST","MODERATE_COMMENT"}
        return {"action":action,"allowed":action not in gated,"requires_user_approval":action in gated}

    def snapshot(self):
        return {"configured":bool(os.getenv("YOUTUBE_CLIENT_ID") and os.getenv("YOUTUBE_CLIENT_SECRET") and os.getenv("YOUTUBE_REFRESH_TOKEN")),"channel_inspection":True,"video_listing":True,"video_metadata_update":True,"analytics":True,"deletion":False,"credential_storage":False,"approval_gated":True}
