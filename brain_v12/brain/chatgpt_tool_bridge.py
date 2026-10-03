from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ToolBridgeRequest:
    tool: str
    arguments: Dict[str, Any]
    request_id: str


@dataclass(frozen=True)
class ToolBridgeResult:
    request_id: str
    ok: bool
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ChatGPTToolBridge:
    """Fail-closed protocol adapter for ChatGPT host tools."""

    def __init__(self, adapter=None):
        self.adapter = adapter

    @property
    def available(self) -> bool:
        return self.adapter is not None and callable(getattr(self.adapter, "dispatch", None))

    def dispatch(self, request: ToolBridgeRequest) -> ToolBridgeResult:
        if not self.available:
            return ToolBridgeResult(
                request_id=request.request_id,
                ok=False,
                status="BRIDGE_UNAVAILABLE",
                error="No ChatGPT host-tool adapter is configured.",
            )
        try:
            raw = self.adapter.dispatch(request)
        except Exception as exc:
            return ToolBridgeResult(
                request_id=request.request_id,
                ok=False,
                status="BRIDGE_FAILED",
                error=str(exc)[:1000],
            )
        if not isinstance(raw, dict):
            return ToolBridgeResult(
                request_id=request.request_id,
                ok=False,
                status="INVALID_BRIDGE_RESULT",
                error="Adapter returned a non-object result.",
            )
        return ToolBridgeResult(
            request_id=request.request_id,
            ok=bool(raw.get("ok")),
            status=str(raw.get("status", "EXECUTED" if raw.get("ok") else "FAILED")),
            result=raw.get("result") if isinstance(raw.get("result"), dict) else raw,
            error=raw.get("error"),
        )

    def status(self) -> Dict[str, Any]:
        return {
            "available": self.available,
            "execution": "delegated",
            "evidence_required": True,
            "fail_closed": True,
            "transport": getattr(self.adapter, "transport_name", None),
        }


class JsonChatGPTToolAdapter:
    """Host-side transport contract using an injected callable.

    The callable receives a JSON-compatible request dictionary and must return
    a JSON object containing ok/status/result/error. No host tool is executed
    by Brain itself; the host owns the callable and its permissions.
    """

    transport_name = "callable"

    def __init__(self, transport):
        self.transport = transport

    def dispatch(self, request: ToolBridgeRequest):
        if not callable(self.transport):
            raise RuntimeError("ChatGPT host transport is not configured")
        payload = {
            "request_id": request.request_id,
            "tool": request.tool,
            "arguments": request.arguments,
        }
        return self.transport(payload)


class HttpChatGPTToolAdapter:
    """HTTP host-gateway adapter for a real ChatGPT tool bridge.

    The gateway is external to Brain and is responsible for invoking the
    actual host capability. Brain sends only a JSON envelope and accepts a
    structured execution result. Missing configuration, non-2xx responses,
    malformed JSON, and transport errors fail closed.
    """

    transport_name = "http"

    def __init__(self, url: str, token: Optional[str] = None, timeout: float = 30.0):
        self.url = str(url or "").strip()
        self.token = token
        self.timeout = float(timeout)

    @classmethod
    def from_environment(cls):
        url = os.getenv("BRAIN_CHATGPT_BRIDGE_URL", "").strip()
        token = os.getenv("BRAIN_CHATGPT_BRIDGE_TOKEN")
        timeout = float(os.getenv("BRAIN_CHATGPT_BRIDGE_TIMEOUT", "30"))
        if not url:
            return None
        return cls(url, token=token, timeout=timeout)

    def dispatch(self, request: ToolBridgeRequest):
        if not self.url:
            raise RuntimeError("BRAIN_CHATGPT_BRIDGE_URL is not configured")
        payload = json.dumps({
            "request_id": request.request_id,
            "tool": request.tool,
            "arguments": request.arguments,
        }, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        req = urllib.request.Request(self.url, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError("bridge HTTP %s: %s" % (exc.code, body))
        except urllib.error.URLError as exc:
            raise RuntimeError("bridge transport error: %s" % exc.reason)
        try:
            result = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("bridge returned invalid JSON: %s" % exc)
        if not isinstance(result, dict):
            raise RuntimeError("bridge returned a non-object JSON response")
        return result


def build_chatgpt_tool_bridge_from_environment() -> ChatGPTToolBridge:
    """Create a fail-closed bridge from BRAIN_CHATGPT_BRIDGE_* settings."""
    adapter = HttpChatGPTToolAdapter.from_environment()
    return ChatGPTToolBridge(adapter)
