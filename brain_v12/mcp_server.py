from __future__ import annotations

import os

from fastapi import Request
from fastapi.responses import JSONResponse

from .app import app as brain_app
from .app import brain_ai, device_bridge, store
from .brain.brain_mcp import build_mcp_router


# Wrapper entrypoint: preserves the existing Brain app and adds /mcp.
brain_app.include_router(build_mcp_router(brain_ai, device_bridge, store))


@brain_app.middleware("http")
async def brain_mcp_auth(request: Request, call_next):
    if request.url.path == "/mcp":
        expected = os.getenv("BRAIN_MCP_TOKEN", "").strip()
        if expected:
            authorization = request.headers.get("authorization", "")
            if authorization != f"Bearer {expected}":
                return JSONResponse(
                    {"ok": False, "status": "MCP_AUTH_REQUIRED"},
                    status_code=401,
                )
    return await call_next(request)


app = brain_app
