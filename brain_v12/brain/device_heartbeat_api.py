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
        payload = body or {}
        raw_body_agent_id = payload.get("agent_id", "")
        if not isinstance(raw_body_agent_id, str):
            raise HTTPException(status_code=422, detail="INVALID_DEVICE_AGENT_ID")
        metadata = payload.get("metadata", {})
        if not isinstance(metadata, dict):
            raise HTTPException(status_code=422, detail="INVALID_DEVICE_METADATA")
        try:
            agent_id = authorize_heartbeat_identity(
                request.headers.get("X-V12-Agent-Id", ""),
                raw_body_agent_id,
                request.headers.get("X-V12-Agent-Key", ""),
                per_agent_registry_configured(),
                device_bridge.authenticate,
            )
        except HeartbeatAuthorizationError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
        return device_bridge.heartbeat(agent_id, metadata)

    return router
