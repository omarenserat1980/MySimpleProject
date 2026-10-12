from __future__ import annotations
import os, httpx
from dataclasses import dataclass

@dataclass
class CanonicalQuranAdapter:
    """Read-only adapter. It never writes or transforms canonical Quran text."""
    base_url: str = "https://apis.quran.foundation"
    client_id: str | None = None
    token: str | None = None

    def __init__(self):
        self.client_id = os.getenv("QF_CLIENT_ID")
        self.token = os.getenv("QF_ACCESS_TOKEN")
        self.base_url = (
            "https://apis.quran.foundation"
            if os.getenv("QF_ENV", "prelive") == "production"
            else "https://apis-prelive.quran.foundation"
        )

    def configured(self) -> bool:
        return bool(self.client_id and self.token)

    def _get(self, path: str, params: dict | None = None) -> dict:
        if not self.configured():
            return {"ok": False, "status": "NOT_CONFIGURED", "source": "Quran Foundation"}
        headers = {"x-auth-token": self.token, "x-client-id": self.client_id}
        with httpx.Client(timeout=30) as client:
            response = client.get(self.base_url + path, headers=headers, params=params or {})
        if response.status_code >= 400:
            return {"ok": False, "status": "UPSTREAM_ERROR", "http_status": response.status_code}
        return {"ok": True, "data": response.json(), "source": "Quran Foundation"}

    def chapters(self) -> dict:
        return self._get("/content/api/v4/chapters")

    def verses(self, chapter: int, page: int = 1, per_page: int = 50) -> dict:
        return self._get(f"/content/api/v4/verses/by_chapter/{chapter}",
                         {"page": page, "per_page": min(per_page, 50)})

    def search(self, query: str) -> dict:
        return self._get("/api/v1/search", {"mode": "advanced", "query": query, "page": 1, "size": 20})
