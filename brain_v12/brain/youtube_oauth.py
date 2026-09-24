"""Google OAuth coordinator for YouTube Data API v3.

The brain never receives or displays Google passwords. The user completes
authorization on Google's consent page. Credentials are supplied to the
runtime through environment variables and token material is kept out of logs.
"""
from __future__ import annotations
import json
import os
from typing import Any
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from cryptography.fernet import Fernet

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
SESSION = {}

class YouTubeOAuth:
    def __init__(self, store):
        self.store = store

    def _fernet(self):
        key=os.getenv("YOUTUBE_TOKEN_ENCRYPTION_KEY")
        if not key: return None
        return Fernet(key.encode())

    def _save_refresh_token(self, token: str):
        f=self._fernet()
        if not f: raise RuntimeError("YOUTUBE_TOKEN_ENCRYPTION_KEY is required")
        self.store.event("YOUTUBE_REFRESH_TOKEN_STORED", {"token_ciphertext": f.encrypt(token.encode()).decode()})

    def _load_refresh_token(self):
        for name,payload in reversed(getattr(self.store,"events",lambda:[])()):
            if name=="YOUTUBE_REFRESH_TOKEN_STORED":
                try: return self._fernet().decrypt(payload["token_ciphertext"].encode()).decode()
                except Exception: return None
        return None

    def configured(self) -> bool:
        return bool(os.getenv("YOUTUBE_CLIENT_ID") and os.getenv("YOUTUBE_CLIENT_SECRET"))

    def _client_config(self) -> dict[str, Any]:
        cid=os.getenv("YOUTUBE_CLIENT_ID")
        secret=os.getenv("YOUTUBE_CLIENT_SECRET")
        if not cid or not secret:
            raise RuntimeError("YouTube OAuth client is not configured")
        return {"web":{"client_id":cid,"client_secret":secret,
                       "auth_uri":"https://accounts.google.com/o/oauth2/auth",
                       "token_uri":"https://oauth2.googleapis.com/token",
                       "redirect_uris":[self.redirect_uri()]}}

    def redirect_uri(self) -> str:
        return os.getenv("YOUTUBE_OAUTH_REDIRECT_URI","")

    def start(self) -> dict[str, Any]:
        if not self.configured() or not self.redirect_uri():
            return {"ok":False,"status":"OAUTH_CONFIG_REQUIRED",
                    "required_env":["YOUTUBE_CLIENT_ID","YOUTUBE_CLIENT_SECRET","YOUTUBE_OAUTH_REDIRECT_URI"]}
        flow=Flow.from_client_config(self._client_config(),scopes=SCOPES,
                                     redirect_uri=self.redirect_uri())
        url,state=flow.authorization_url(access_type="offline",include_granted_scopes="true",prompt="consent")
        SESSION[state]=flow
        self.store.event("YOUTUBE_OAUTH_STARTED",{"state_hash":state[:12]})
        return {"ok":True,"status":"AUTHORIZATION_REQUIRED","authorization_url":url}

    def callback(self, code: str, state: str) -> dict[str, Any]:
        flow=SESSION.pop(state,None)
        if not flow:
            return {"ok":False,"status":"INVALID_OR_EXPIRED_OAUTH_STATE"}
        flow.fetch_token(code=code)
        creds=flow.credentials
        if not creds.refresh_token:
            return {"ok":False,"status":"NO_REFRESH_TOKEN","reason":"Google did not return offline authorization"}
        self._save_refresh_token(creds.refresh_token)
        self.store.event("YOUTUBE_OAUTH_AUTHORIZED",{"scopes":list(creds.scopes or SCOPES)})
        return {"ok":True,"status":"AUTHORIZED","scopes":list(creds.scopes or SCOPES)}

    def credentials(self) -> Credentials | None:
        refresh=self._load_refresh_token() or os.getenv("YOUTUBE_REFRESH_TOKEN")
        cid=os.getenv("YOUTUBE_CLIENT_ID")
        secret=os.getenv("YOUTUBE_CLIENT_SECRET")
        if not (refresh and cid and secret):
            return None
        return Credentials(token=None,refresh_token=refresh,token_uri="https://oauth2.googleapis.com/token",
                           client_id=cid,client_secret=secret,scopes=SCOPES)

    def snapshot(self) -> dict[str, Any]:
        return {"ok":True,"configured":self.configured(),
                "authorized":bool(self._load_refresh_token() or os.getenv("YOUTUBE_REFRESH_TOKEN")),
                "scope":"youtube.upload",
                "credentials_in_logs":False}
