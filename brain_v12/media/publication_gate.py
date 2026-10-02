"""External publication gate: authorization is mandatory."""
from __future__ import annotations

def authorize(request: dict, approved: bool = False) -> dict:
    if not approved:
        return {"status": "REQUIRES_AUTHORIZATION", "action": request.get("action", "publish_external")}
    return {
        "status": "AUTHORIZED",
        "action": request.get("action", "publish_external"),
        "content": request.get("content", ""),
    }
