"""Safe adapter contract for self-hosted VoicEra."""
from __future__ import annotations
import os, urllib.request, json

class VoicEraAdapter:
    def __init__(self, endpoint: str | None = None):
        self.endpoint = endpoint or os.getenv("BRAIN_VOICERA_ENDPOINT")

    def health(self) -> dict:
        if not self.endpoint:
            return {"status":"UNCONFIGURED"}
        try:
            with urllib.request.urlopen(self.endpoint, timeout=10) as response:
                return {"status":"HEALTHY","http_status":response.status}
        except Exception as exc:
            return {"status":"FAILED","error":repr(exc)}
