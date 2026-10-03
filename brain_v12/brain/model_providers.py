from __future__ import annotations

import os
from typing import Any, Dict, List
import httpx


def _payload(user_text: str, context: str, instructions: str) -> str:
    parts = []
    if instructions:
        parts.append("Instructions:\n" + instructions)
    if context:
        parts.append("Context:\n" + context)
    parts.append("User:\n" + user_text)
    return "\n\n".join(parts)


class HttpModelProvider:
    name = "http-model"

    def __init__(self, model: str, timeout: float = 90.0):
        self.model = model
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return False

    def status(self) -> Dict[str, Any]:
        return {"provider": self.name, "configured": self.configured, "model": self.model}

    def respond(self, user_text: str, context: str = "", instructions: str = "") -> Dict[str, Any]:
        raise NotImplementedError


class OpenAIModelProvider(HttpModelProvider):
    name = "openai"

    def __init__(self):
        super().__init__(os.getenv("OPENAI_MODEL", "gpt-5"))
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")

    @property
    def configured(self):
        return bool(self.api_key)

    def respond(self, user_text, context="", instructions=""):
        if not self.configured:
            return {"ok": False, "error": "OPENAI_NOT_CONFIGURED"}
        payload = {"model": self.model, "input": _payload(user_text, context, instructions)}
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.post(f"{self.base_url}/responses", headers=headers, json=payload)
            if r.status_code >= 400:
                return {"ok": False, "error": "OPENAI_API_ERROR", "status_code": r.status_code, "detail": r.text[:2000]}
            data = r.json()
            text = data.get("output_text", "")
            if not text:
                for item in data.get("output", []):
                    for part in item.get("content", []):
                        if part.get("type") in {"output_text", "text"}:
                            text += part.get("text", "")
            return {"ok": True, "result": {"reply": text, "model": self.model, "response_id": data.get("id")}}
        except httpx.HTTPError as exc:
            return {"ok": False, "error": "OPENAI_NETWORK_ERROR", "detail": str(exc)[:1000]}


class GeminiModelProvider(HttpModelProvider):
    name = "gemini"

    def __init__(self):
        super().__init__(os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.base_url = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")

    @property
    def configured(self):
        return bool(self.api_key)

    def respond(self, user_text, context="", instructions=""):
        if not self.configured:
            return {"ok": False, "error": "GEMINI_NOT_CONFIGURED"}
        payload = {"contents": [{"role": "user", "parts": [{"text": _payload(user_text, context, instructions)}]}]}
        url = f"{self.base_url}/models/{self.model}:generateContent"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.post(url, params={"key": self.api_key}, json=payload)
            if r.status_code >= 400:
                return {"ok": False, "error": "GEMINI_API_ERROR", "status_code": r.status_code, "detail": r.text[:2000]}
            data = r.json()
            text = ""
            for candidate in data.get("candidates", []):
                for part in candidate.get("content", {}).get("parts", []):
                    text += part.get("text", "")
            return {"ok": True, "result": {"reply": text, "model": self.model}}
        except httpx.HTTPError as exc:
            return {"ok": False, "error": "GEMINI_NETWORK_ERROR", "detail": str(exc)[:1000]}


class OllamaModelProvider(HttpModelProvider):
    name = "ollama"

    def __init__(self):
        super().__init__(os.getenv("OLLAMA_MODEL", "qwen3:8b"))
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")

    @property
    def configured(self):
        return bool(os.getenv("OLLAMA_ENABLED", "0").lower() in {"1", "true", "yes", "on"})

    def respond(self, user_text, context="", instructions=""):
        if not self.configured:
            return {"ok": False, "error": "OLLAMA_NOT_ENABLED"}
        payload = {"model": self.model, "prompt": _payload(user_text, context, instructions), "stream": False}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.post(f"{self.base_url}/api/generate", json=payload)
            if r.status_code >= 400:
                return {"ok": False, "error": "OLLAMA_API_ERROR", "status_code": r.status_code, "detail": r.text[:2000]}
            data = r.json()
            return {"ok": True, "result": {"reply": data.get("response", ""), "model": data.get("model", self.model)}}
        except httpx.HTTPError as exc:
            return {"ok": False, "error": "OLLAMA_NETWORK_ERROR", "detail": str(exc)[:1000]}


def configured_model_providers() -> List[HttpModelProvider]:
    providers = [OpenAIModelProvider(), GeminiModelProvider(), OllamaModelProvider()]
    return [p for p in providers if p.configured]
