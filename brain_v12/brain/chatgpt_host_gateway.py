"""ChatGPT host-tool gateway contract for Electronic Brain.

This module is intentionally transport-only. The ChatGPT host owns the actual
tool dispatcher; Brain never receives host credentials and never fabricates a
tool result. A host process can mount this protocol behind an authenticated
HTTP endpoint and inject a dispatcher callable.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional
from uuid import uuid4


class ChatGPTHostGateway:
    def __init__(self, dispatcher: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None):
        self.dispatcher = dispatcher

    @property
    def available(self) -> bool:
        return callable(self.dispatcher)

    def dispatch(self, tool: str, arguments: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None):
        request_id = request_id or str(uuid4())
        arguments = arguments if isinstance(arguments, dict) else {}
        if not self.available:
            return {
                "ok": False,
                "status": "HOST_DISPATCHER_UNAVAILABLE",
                "request_id": request_id,
                "error": "ChatGPT host dispatcher is not attached.",
            }
        try:
            result = self.dispatcher(tool, arguments)
        except Exception as exc:
            return {
                "ok": False,
                "status": "HOST_DISPATCH_FAILED",
                "request_id": request_id,
                "error": str(exc)[:1000],
            }
        if not isinstance(result, dict):
            return {
                "ok": False,
                "status": "INVALID_HOST_RESULT",
                "request_id": request_id,
                "error": "Host dispatcher must return a JSON object.",
            }
        return {
            "request_id": request_id,
            "ok": bool(result.get("ok")),
            "status": str(result.get("status", "EXECUTED" if result.get("ok") else "FAILED")),
            "result": result.get("result"),
            "error": result.get("error"),
            "evidence": result.get("evidence"),
        }

    def status(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "available": self.available,
            "dispatcher_attached": self.available,
            "fail_closed": True,
            "evidence_required": True,
        }


def build_host_gateway(dispatcher=None) -> ChatGPTHostGateway:
    return ChatGPTHostGateway(dispatcher=dispatcher)
