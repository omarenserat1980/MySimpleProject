from __future__ import annotations

import json
from typing import Any, Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse


PROTOCOL_VERSION = "2026-07-28"
SUPPORTED_PROTOCOL_VERSIONS = {PROTOCOL_VERSION, "2025-11-25", "2025-06-18"}


def build_mcp_router(brain_ai, device_bridge, store) -> APIRouter:
    """Expose a minimal, stateless MCP Streamable HTTP surface.

    This implementation deliberately avoids adding an MCP SDK dependency to
    Brain's existing FastAPI/Pydantic environment.
    """

    router = APIRouter()
    tools: dict[str, dict[str, Any]] = {}

    def register(
        name: str,
        description: str,
        input_schema: dict[str, Any],
        handler: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        tools[name] = {
            "name": name,
            "description": description,
            "inputSchema": input_schema,
            "_handler": handler,
        }

    def status_handler(_: dict[str, Any]) -> dict[str, Any]:
        return {
            "ok": True,
            "source": "electronic-brain",
            "status": brain_ai.status(),
        }

    def device_handler(_: dict[str, Any]) -> dict[str, Any]:
        try:
            result = device_bridge.agent_status()
        except Exception as exc:
            return {
                "ok": False,
                "status": "DEVICE_STATUS_ERROR",
                "error": str(exc)[:500],
            }
        return {
            "ok": True,
            "source": "electronic-brain",
            "device": result,
        }

    def evidence_handler(arguments: dict[str, Any]) -> dict[str, Any]:
        limit = max(1, min(int(arguments.get("limit", 10)), 50))
        try:
            with store.connect() as con:
                rows = con.execute(
                    "SELECT * FROM events ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            events = [dict(row) for row in rows]
        except Exception as exc:
            return {
                "ok": False,
                "status": "EVIDENCE_READ_ERROR",
                "error": str(exc)[:500],
            }
        return {
            "ok": True,
            "source": "electronic-brain",
            "events": events,
            "count": len(events),
        }

    def chat_handler(arguments: dict[str, Any]) -> dict[str, Any]:
        message = str(arguments.get("message", "")).strip()
        if not message:
            return {"ok": False, "status": "EMPTY_MESSAGE"}
        result = brain_ai.chat(message, approved=False)
        return {
            "ok": bool(result.ok),
            "status": result.mode,
            "reply": result.reply,
            "model": result.model,
            "tool_calls": result.tool_calls,
            "evidence": result.evidence,
            "error": result.error,
        }

    register(
        "brain.status",
        "Read the current Electronic Brain status and governed capabilities.",
        {"type": "object", "properties": {}, "additionalProperties": False},
        status_handler,
    )
    register(
        "brain.device_status",
        "Read fresh status for the configured Brain device bridge.",
        {"type": "object", "properties": {}, "additionalProperties": False},
        device_handler,
    )
    register(
        "brain.evidence",
        "Read recent Brain event evidence without mutating state.",
        {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 50}
            },
            "additionalProperties": False,
        },
        evidence_handler,
    )
    register(
        "brain.chat",
        "Ask Electronic Brain through its governed BrainAI chat loop.",
        {
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
            "additionalProperties": False,
        },
        chat_handler,
    )

    def rpc_result(request_id: Any, result: dict[str, Any]) -> JSONResponse:
        return JSONResponse({"jsonrpc": "2.0", "id": request_id, "result": result})

    def rpc_error(request_id: Any, code: int, message: str) -> JSONResponse:
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": code, "message": message},
            }
        )

    @router.get("/mcp")
    async def mcp_get(request: Request):
        # Stateless MCP does not require an event stream for these read-only
        # request/response tools. A GET is kept for discovery/health clients.
        version = request.headers.get("MCP-Protocol-Version", PROTOCOL_VERSION)
        if version not in SUPPORTED_PROTOCOL_VERSIONS:
            return JSONResponse(
                {"error": "UNSUPPORTED_MCP_PROTOCOL_VERSION"},
                status_code=400,
            )
        return JSONResponse(
            {
                "name": "Electronic Brain",
                "protocolVersion": PROTOCOL_VERSION,
                "transport": "streamable-http",
            }
        )

    @router.post("/mcp")
    async def mcp_post(request: Request):
        version = request.headers.get("MCP-Protocol-Version")
        if version not in SUPPORTED_PROTOCOL_VERSIONS:
            return JSONResponse(
                {"error": "UNSUPPORTED_MCP_PROTOCOL_VERSION"},
                status_code=400,
                headers={"MCP-Protocol-Version": PROTOCOL_VERSION},
            )

        try:
            body = await request.json()
        except Exception:
            return rpc_error(None, -32700, "Parse error")

        if not isinstance(body, dict):
            return rpc_error(None, -32600, "Invalid Request")

        method = str(body.get("method", ""))
        request_id = body.get("id")
        params = body.get("params") or {}

        if method == "initialize":
            if version == PROTOCOL_VERSION:
                return rpc_result(
                    request_id,
                    {
                        "protocolVersion": PROTOCOL_VERSION,
                        "capabilities": {"tools": {"listChanged": False}},
                        "serverInfo": {
                            "name": "Electronic Brain",
                            "version": "14.0-mcp",
                        },
                    },
                )
            return rpc_result(
                request_id,
                {
                    "protocolVersion": version,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {
                        "name": "Electronic Brain",
                        "version": "14.0-mcp",
                    },
                },
            )

        if method in {"notifications/initialized", "notifications/cancelled"}:
            return JSONResponse(status_code=202, content=None)

        if method == "ping":
            return rpc_result(request_id, {})

        if method == "server/discover":
            return rpc_result(
                request_id,
                {
                    "serverInfo": {
                        "name": "Electronic Brain",
                        "version": "14.0-mcp",
                    },
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                },
            )

        if method == "tools/list":
            visible = [
                {
                    "name": item["name"],
                    "description": item["description"],
                    "inputSchema": item["inputSchema"],
                }
                for item in sorted(tools.values(), key=lambda x: x["name"])
            ]
            return rpc_result(request_id, {"tools": visible})

        if method == "tools/call":
            name = str(params.get("name", ""))
            arguments = params.get("arguments") or {}
            item = tools.get(name)
            if item is None:
                return rpc_error(request_id, -32602, f"Unknown tool: {name}")
            if not isinstance(arguments, dict):
                return rpc_error(request_id, -32602, "arguments must be an object")

            try:
                result = item["_handler"](arguments)
            except Exception as exc:
                result = {
                    "ok": False,
                    "status": "TOOL_EXCEPTION",
                    "error": str(exc)[:500],
                }

            text = json.dumps(result, ensure_ascii=False, default=str)
            return rpc_result(
                request_id,
                {
                    "content": [{"type": "text", "text": text}],
                    "structuredContent": result,
                    "isError": not bool(result.get("ok")),
                },
            )

        if method.startswith("resources/") or method.startswith("prompts/"):
            return rpc_error(request_id, -32601, "Method not found")

        return rpc_error(request_id, -32601, "Method not found")

    return router
