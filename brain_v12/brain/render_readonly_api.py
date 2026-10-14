"""Authenticated, read-only Brain API for Render diagnostics.

The integration is feature-disabled by default and always honors Brain Mouse policy.
It exposes no deploy, restart, environment mutation, or other write operation.
"""
from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from .control_auth import require_control_key
from .render_readonly_connector import RenderConnectorError, RenderReadOnlyClient, _policy_allows_render

router = APIRouter(tags=["brain-render-readonly"])


def _client() -> RenderReadOnlyClient:
    enabled = os.getenv("BRAIN_RENDER_READONLY_ENABLED", "").strip().lower() == "true"
    return RenderReadOnlyClient.from_environment(enabled=enabled)


def _translate_error(exc: RenderConnectorError) -> HTTPException:
    message = str(exc)
    if "disabled" in message or "policy blocks" in message:
        return HTTPException(status_code=423, detail=message)
    if "credential is not configured" in message:
        return HTTPException(status_code=503, detail=message)
    return HTTPException(status_code=502, detail=message)


@router.get("/api/render-readonly/status")
def render_readonly_status(request: Request) -> dict[str, Any]:
    require_control_key(request)
    enabled = os.getenv("BRAIN_RENDER_READONLY_ENABLED", "").strip().lower() == "true"
    policy_allows = _policy_allows_render()
    return {
        "ok": True,
        "connector": "render-readonly",
        "feature_enabled": enabled,
        "policy_allows_external_render": policy_allows,
        "connection_status": "NOT_PROBED",
        "network_request_made": False,
        "write_operations_available": False,
        "reason": (
            "POLICY_BLOCKED"
            if not policy_allows
            else "FEATURE_DISABLED"
            if not enabled
            else "NOT_PROBED"
        ),
    }


@router.get("/api/render-readonly/services/{service_id}")
def render_readonly_service(service_id: str, request: Request) -> Any:
    require_control_key(request)
    try:
        return {"ok": True, "service": _client().service(service_id)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RenderConnectorError as exc:
        raise _translate_error(exc) from exc


@router.get("/api/render-readonly/services/{service_id}/deploys")
def render_readonly_deploys(
    service_id: str, request: Request, limit: int = 10
) -> Any:
    require_control_key(request)
    try:
        return {"ok": True, "deploys": _client().deploys(service_id, limit=limit)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RenderConnectorError as exc:
        raise _translate_error(exc) from exc


@router.get("/api/render-readonly/logs/{resource_id}")
def render_readonly_logs(
    resource_id: str,
    request: Request,
    start_time: str,
    end_time: str,
    limit: int = 100,
) -> Any:
    require_control_key(request)
    try:
        return {
            "ok": True,
            "logs": _client().logs(
                resource_id, start_time=start_time, end_time=end_time, limit=limit
            ),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RenderConnectorError as exc:
        raise _translate_error(exc) from exc
