from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ToolCallRequest:
    call_id: str
    name: str
    arguments: Dict[str, Any]

    @classmethod
    def from_payload(cls, payload: Any) -> Optional["ToolCallRequest"]:
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                return None
        if not isinstance(payload, dict) or payload.get("type") != "tool_call":
            return None
        name = payload.get("name")
        arguments = payload.get("arguments", {})
        call_id = payload.get("call_id", "")
        if not isinstance(name, str) or not name.strip():
            return None
        if not isinstance(arguments, dict):
            return None
        if not isinstance(call_id, str) or not call_id.strip():
            return None
        return cls(call_id=call_id, name=name, arguments=arguments)


@dataclass
class ToolCallResult:
    call_id: str
    name: str
    status: str
    ok: bool
    result: Dict[str, Any]

    def evidence(self) -> Dict[str, Any]:
        return {
            "type": "tool",
            "call_id": self.call_id,
            "tool": self.name,
            "status": self.status,
            "ok": self.ok,
            "result": self.result,
        }


def parse_tool_call(payload: Any) -> Optional[ToolCallRequest]:
    return ToolCallRequest.from_payload(payload)
