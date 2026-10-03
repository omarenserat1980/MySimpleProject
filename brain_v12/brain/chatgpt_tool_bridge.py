from __future__ import annotations

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
        }
