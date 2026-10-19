"""FastAPI router for authenticated device heartbeats.

The router factory accepts a bridge instance so endpoint behavior can be tested
with an isolated in-memory fake without importing the full Brain application.
"""
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from .device_heartbeat_auth import (
    HeartbeatAuthorizationError,
    authorize_heartbeat_identity,
)


def build_device_heartbeat_router(
    device_bridge: Any,
    per_agent_registry_configured: Callable[[], bool],
) -> APIRouter:
    router = APIRouter()

    @router.post("/api/device/heartbeat")
    def device_heartbeat(request: Request, body: dict | None = None):
        try:
            agent_id = authorize_heartbeat_identity(
                request.headers.get("X-V12-Agent-Id", ""),
                str((body or {}).get("agent_id", "")),
                request.headers.get("X-V12-Agent-Key", ""),
                per_agent_registry_configured(),
                device_bridge.authenticate,
            )
        except HeartbeatAuthorizationError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
        return device_bridge.heartbeat(agent_id, (body or {}).get("metadata") or {})

    return router
