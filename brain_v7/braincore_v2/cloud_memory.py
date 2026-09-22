"""Cloud memory adapter for the Electronic Brain V9.

Uses a Supabase-compatible REST endpoint when configured. No credentials are stored
in source code. If cloud settings are absent, operations safely become no-ops.
Expected table: brain_memories(id, user_id, kind, content, importance, created_at).
"""

import os
from typing import Any

import httpx


class CloudMemory:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.key = os.getenv("SUPABASE_KEY", "")
        self.table = os.getenv("MEMORY_TABLE", "brain_memories")
        self.timeout = float(os.getenv("MEMORY_TIMEOUT", "10"))

    @property
    def configured(self) -> bool:
        return bool(self.url and self.key)

    def status(self) -> dict[str, Any]:
        return {
            "configured": self.configured,
            "provider": "supabase_rest",
            "table": self.table,
        }

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def save(
        self,
        user_id: str,
        kind: str,
        content: str,
        importance: float = 0.5,
    ) -> bool:
        if not self.configured:
            return False
        payload = {
            "user_id": user_id,
            "kind": kind,
            "content": content,
            "importance": max(0.0, min(1.0, float(importance))),
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.url}/rest/v1/{self.table}",
                    headers=self._headers(),
                    json=payload,
                )
                response.raise_for_status()
            return True
        except Exception:
            return False

    def recall(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        if not self.configured:
            return []
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.url}/rest/v1/{self.table}",
                    headers=self._headers(),
                    params={
                        "user_id": f"eq.{user_id}",
                        "select": "id,user_id,kind,content,importance,created_at",
                        "order": "importance.desc,created_at.desc",
                        "limit": max(1, min(50, int(limit))),
                    },
                )
                response.raise_for_status()
                data = response.json()
            return data if isinstance(data, list) else []
        except Exception:
            return []
