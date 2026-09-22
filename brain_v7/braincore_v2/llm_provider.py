"""Optional OpenAI-compatible language model provider for Brain V9.

The provider is deliberately optional. If no API key is configured, the brain keeps
working with its local deterministic conversation layer.
"""

import os
from typing import Any

import httpx


class LLMProvider:
    def __init__(self):
        self.base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.model = os.getenv("LLM_MODEL", "gpt-5")
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.timeout = float(os.getenv("LLM_TIMEOUT", "60"))

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def status(self) -> dict[str, Any]:
        return {
            "configured": self.configured,
            "model": self.model,
            "base_url": self.base_url,
        }

    def reply(self, messages: list[dict[str, str]]) -> str | None:
        if not self.configured:
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
            choices = data.get("choices") or []
            if not choices:
                return None
            message = choices[0].get("message") or {}
            content = message.get("content")
            return content.strip() if isinstance(content, str) and content.strip() else None
        except Exception:
            # A provider failure must never pretend that a response was generated.
            return None
