from __future__ import annotations

import os

from fastapi import Request
from fastapi.responses import JSONResponse
from mcp.server.fastmcp import FastMCP

from .app import app as brain_app
from .brain.brain_mcp import build_brain_mcp


# This wrapper preserves the existing Brain application and only adds the MCP
# surface. It does not replace the normal app entrypoint.
mcp: FastMCP = build_brain_mcp(
    brain_ai=__import__(__package__ + ".app", fromlist=["brain_ai"]).brain_ai,
    device_bridge=__import__(__package__ + ".app", fromlist=["device_bridge"]).device_bridge,
    store=__import__(__package__ + ".app", fromlist=["store"]).store,
)

mcp_app = mcp.streamable_http_app()

# FastMCP's Streamable HTTP app owns its session-manager lifespan.
# The existing Brain app has no custom lifespan, so this is safe for the
# wrapper entrypoint.
brain_app.router.lifespan_context = mcp_app.lifespan


@brain_app.middleware("http")
async def brain_mcp_auth(request: Request, call_next):
    if request.url.path.startswith("/mcp"):
        expected = os.getenv("BRAIN_MCP_TOKEN", "").strip()
        if expected:
            authorization = request.headers.get("authorization", "")
            if authorization != f"Bearer {expected}":
                return JSONResponse(
                    {"ok": False, "status": "MCP_AUTH_REQUIRED"},
                    status_code=401,
                )
    return await call_next(request)


brain_app.mount("/mcp", mcp_app)
app = brain_app
