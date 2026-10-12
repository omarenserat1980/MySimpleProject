from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from .chat_request_ledger import ChatRequestLedger
from .chat_session_store import ChatSessionStore


PROTOCOL_VERSION = "2026-07-28"
SUPPORTED_PROTOCOL_VERSIONS = {PROTOCOL_VERSION, "2025-11-25", "2025-06-18"}
WIDGET_URI = "ui://widget/electronic-brain-chat.html"
WIDGET_PATH = Path(__file__).resolve().parents[1] / "web" / "brain-chat-widget.html"
WIDGET_MIME_TYPE = "text/html;profile=mcp-app"


def build_mcp_router(brain_ai, device_bridge, store, chat_sessions=None) -> APIRouter:
    """Expose Brain tools and an MCP Apps-compatible embedded chat widget.

    The existing HTTP authentication boundary remains owned by mcp_server.py.
    The widget uses MCP tools only; it never receives server credentials.
    """

    router = APIRouter()
    tools: dict[str, dict[str, Any]] = {}
    chat_sessions = chat_sessions or ChatSessionStore(
        getattr(store, "path", Path(__file__).resolve().parents[1] / "brain_v12.db")
    )
    chat_sessions.init()
    ledger = ChatRequestLedger(chat_sessions.path)
    ledger.init()
    widget_html = WIDGET_PATH.read_text(encoding="utf-8")

    widget_resource_meta = {
        "ui": {
            "prefersBorder": True,
            "domain": "https://brain-control-plane-main.onrender.com",
            "csp": {
                "connectDomains": ["https://brain-control-plane-main.onrender.com"],
                "resourceDomains": [],
            },
        },
        "openai/widgetDescription": (
            "واجهة عربية للعقل الإلكتروني. يمكنها بدء جلسات محادثة محفوظة "
            "وإرسال حرف ع تلقائيًا ضمن حد آمن للدورات."
        ),
    }

    def register(
        name: str,
        description: str,
        input_schema: dict[str, Any],
        handler: Callable[[dict[str, Any]], dict[str, Any]],
        meta: dict[str, Any] | None = None,
    ) -> None:
        tools[name] = {
            "name": name,
            "description": description,
            "inputSchema": input_schema,
            "_handler": handler,
            **({"_meta": meta} if meta else {}),
        }

    def status_handler(_: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "source": "electronic-brain", "status": brain_ai.status()}

    def device_handler(_: dict[str, Any]) -> dict[str, Any]:
        try:
            result = device_bridge.agent_status()
        except Exception as exc:
            return {"ok": False, "status": "DEVICE_STATUS_ERROR", "error": str(exc)[:500]}
        return {"ok": True, "source": "electronic-brain", "device": result}

    def evidence_handler(arguments: dict[str, Any]) -> dict[str, Any]:
        limit = max(1, min(int(arguments.get("limit", 10)), 50))
        try:
            with store.connect() as con:
                rows = con.execute(
                    "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
                ).fetchall()
            events = [dict(row) for row in rows]
        except Exception as exc:
            return {"ok": False, "status": "EVIDENCE_READ_ERROR", "error": str(exc)[:500]}
        return {"ok": True, "source": "electronic-brain", "events": events, "count": len(events)}

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

    def open_widget_handler(_: dict[str, Any]) -> dict[str, Any]:
        return {
            "ok": True,
            "widget": "electronic-brain-chat",
            "status": "READY_TO_RENDER",
            "message": "افتح واجهة محادثة Electronic Brain المدمجة.",
        }

    def create_chat_session(arguments: dict[str, Any]) -> dict[str, Any]:
        title = str(arguments.get("title", "دورة ع")).strip()[:120] or "دورة ع"
        key = str(arguments.get("client_session_key", "")).strip()[:160]
        # The caller supplies a stable cycle key. Reuse its existing session if
        # a widget reload/retry repeats creation after the database commit.
        if key:
            device_key = "chatgpt-widget:" + key
            with chat_sessions.connect() as con:
                # Enforce uniqueness in SQLite as well as in the widget. Two
                # overlapping iframe requests must not create two sessions.
                con.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_chatgpt_widget_cycle_key "
                    "ON chat_sessions(device_id) WHERE device_id LIKE 'chatgpt-widget:%'"
                )
                row = con.execute(
                    "SELECT id FROM chat_sessions WHERE device_id=? ORDER BY created_at LIMIT 1",
                    (device_key,),
                ).fetchone()
            if row:
                session = chat_sessions.get(row["id"])
                if session:
                    return {"ok": True, "session": session, "idempotent_replay": True}
            try:
                session = chat_sessions.create(title, device_id=device_key)
            except sqlite3.IntegrityError:
                # Another request won the race after our initial lookup.
                with chat_sessions.connect() as con:
                    row = con.execute(
                        "SELECT id FROM chat_sessions WHERE device_id=?", (device_key,)
                    ).fetchone()
                if not row:
                    raise
                session = chat_sessions.get(row["id"])
                if not session:
                    raise RuntimeError("CHAT_SESSION_IDEMPOTENCY_RECOVERY_FAILED")
                return {"ok": True, "session": session, "idempotent_replay": True}
        else:
            session = chat_sessions.create(title)
        return {"ok": True, "session": session, "idempotent_replay": False}

    def send_chat_message(arguments: dict[str, Any]) -> dict[str, Any]:
        session_id = str(arguments.get("session_id", "")).strip()
        message = str(arguments.get("message", "")).strip()
        client_id = str(arguments.get("client_message_id", "")).strip()[:200]
        if not session_id or not message or len(message) > 4000 or not client_id:
            return {"ok": False, "status": "INVALID_CHAT_MESSAGE"}
        session = chat_sessions.get(session_id)
        if session is None:
            return {"ok": False, "status": "SESSION_NOT_FOUND"}

        request_hash = hashlib.sha256(
            json.dumps(
                {"message": message, "approved": False},
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        claimed = ledger.claim(session_id, client_id, request_hash)
        if claimed["status"] == "COMPLETED":
            return {
                "ok": bool(claimed["response"].get("ok")),
                "session": chat_sessions.get(session_id),
                "response": claimed["response"],
                "idempotent_replay": True,
            }
        if claimed["status"] == "ID_CONFLICT":
            return {"ok": False, "status": "CLIENT_MESSAGE_ID_CONFLICT", "retryable": False}
        if claimed["status"] == "IN_PROGRESS":
            return {"ok": False, "status": "REQUEST_IN_PROGRESS", "retryable": True}

        # Recover the window where the assistant reply was persisted but the
        # ledger completion was interrupted by a process restart.
        current = chat_sessions.get(session_id) or {}
        recovered = next(
            (
                item.get("metadata", {})
                for item in reversed(current.get("messages", []))
                if item.get("role") == "assistant"
                and item.get("metadata", {}).get("client_message_id") == client_id
            ),
            None,
        )
        if recovered is not None:
            ledger.complete(session_id, client_id, recovered)
            return {
                "ok": bool(recovered.get("ok")),
                "session": chat_sessions.get(session_id),
                "response": recovered,
                "idempotent_replay": True,
            }

        try:
            chat_sessions.add_message(
                session_id, "user", message, client_message_id=client_id
            )
            history = chat_sessions.context_messages(session_id, limit=24)
            memory = chat_sessions.get_memory(session_id) or {}
            context_lines = ["[{}] {}".format(item["role"], item["content"]) for item in history]
            instructions = "واجهة ChatGPT المدمجة للعقل الإلكتروني. الوضع الآمن: لا تنفذ إجراءات خارجية."
            if memory.get("summary"):
                instructions += "\n\n[BRAIN_SESSION_MEMORY]\n" + memory["summary"]
            if context_lines:
                instructions += "\n\n[BRAIN_SESSION_CONTEXT]\n" + "\n".join(context_lines)
            result = brain_ai.chat(message, instructions, approved=False)
            response = {
                "role": "assistant",
                "content": result.reply,
                "ok": bool(result.ok),
                "mode": result.mode,
                "model": result.model,
                "tool_calls": result.tool_calls,
                "evidence": result.evidence,
                "error": result.error,
                "client_message_id": client_id,
            }
            chat_sessions.add_message(session_id, "assistant", result.reply, response)
            ledger.complete(session_id, client_id, response)
            return {
                "ok": bool(result.ok),
                "session": chat_sessions.get(session_id),
                "response": response,
                "idempotent_replay": False,
            }
        except Exception:
            ledger.fail(session_id, client_id)
            raise

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
            "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 50}},
            "additionalProperties": False,
        },
        evidence_handler,
    )
    register(
        "brain.chat",
        "Ask Electronic Brain through its governed BrainAI chat loop. No external actions are approved.",
        {
            "type": "object",
            "properties": {"message": {"type": "string", "minLength": 1, "maxLength": 4000}},
            "required": ["message"],
            "additionalProperties": False,
        },
        chat_handler,
    )
    register(
        "brain.open_chat_widget",
        "Open the embedded Arabic Electronic Brain chat interface. Use this tool when the user asks to open or interact with the Brain chat simulator.",
        {"type": "object", "properties": {}, "additionalProperties": False},
        open_widget_handler,
        {
            "ui": {"resourceUri": WIDGET_URI, "visibility": "model"},
            "openai/outputTemplate": WIDGET_URI,
            "openai/toolInvocation/invoking": "فتح محاكي العقل الإلكتروني…",
            "openai/toolInvocation/invoked": "المحاكي جاهز",
        },
    )
    register(
        "brain.chat_session_create",
        "Create or idempotently recover a persistent Brain chat session for the embedded ChatGPT widget.",
        {
            "type": "object",
            "properties": {
                "title": {"type": "string", "maxLength": 120},
                "client_session_key": {"type": "string", "maxLength": 160},
            },
            "additionalProperties": False,
        },
        create_chat_session,
    )
    register(
        "brain.chat_session_send",
        "Send a message to a persistent Brain chat session. Reusing client_message_id is idempotent. External actions remain unapproved.",
        {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "minLength": 1},
                "message": {"type": "string", "minLength": 1, "maxLength": 4000},
                "client_message_id": {"type": "string", "minLength": 1, "maxLength": 200},
            },
            "required": ["session_id", "message", "client_message_id"],
            "additionalProperties": False,
        },
        send_chat_message,
    )

    def rpc_result(request_id: Any, result: dict[str, Any]) -> JSONResponse:
        return JSONResponse({"jsonrpc": "2.0", "id": request_id, "result": result})

    def rpc_error(request_id: Any, code: int, message: str) -> JSONResponse:
        return JSONResponse(
            {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
        )

    @router.get("/mcp")
    async def mcp_get(request: Request):
        version = request.headers.get("MCP-Protocol-Version", PROTOCOL_VERSION)
        if version not in SUPPORTED_PROTOCOL_VERSIONS:
            return JSONResponse({"error": "UNSUPPORTED_MCP_PROTOCOL_VERSION"}, status_code=400)
        return JSONResponse(
            {"name": "Electronic Brain", "protocolVersion": PROTOCOL_VERSION, "transport": "streamable-http"}
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
            return rpc_result(
                request_id,
                {
                    "protocolVersion": version,
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"subscribe": False, "listChanged": False},
                    },
                    "serverInfo": {"name": "Electronic Brain", "version": "14.1-mcp-apps"},
                    "instructions": "Use brain.open_chat_widget to render the embedded Arabic Brain chat UI.",
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
                    "serverInfo": {"name": "Electronic Brain", "version": "14.1-mcp-apps"},
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"subscribe": False, "listChanged": False},
                    },
                },
            )
        if method == "tools/list":
            visible = [
                {
                    "name": item["name"],
                    "description": item["description"],
                    "inputSchema": item["inputSchema"],
                    **({"_meta": item["_meta"]} if item.get("_meta") else {}),
                }
                for item in sorted(tools.values(), key=lambda x: x["name"])
            ]
            return rpc_result(request_id, {"tools": visible})
        if method == "resources/list":
            return rpc_result(
                request_id,
                {
                    "resources": [
                        {
                            "uri": WIDGET_URI,
                            "name": "Electronic Brain Chat Widget",
                            "description": "Arabic RTL chat widget for ChatGPT Apps.",
                            "mimeType": WIDGET_MIME_TYPE,
                        }
                    ]
                },
            )
        if method == "resources/read":
            if str(params.get("uri", "")) != WIDGET_URI:
                return rpc_error(request_id, -32602, "Unknown resource URI")
            return rpc_result(
                request_id,
                {
                    "contents": [
                        {
                            "uri": WIDGET_URI,
                            "mimeType": WIDGET_MIME_TYPE,
                            "text": widget_html,
                            "_meta": widget_resource_meta,
                        }
                    ]
                },
            )
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
                result = {"ok": False, "status": "TOOL_EXCEPTION", "error": str(exc)[:500]}
            return rpc_result(
                request_id,
                {
                    "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, default=str)}],
                    "structuredContent": result,
                    "isError": not bool(result.get("ok")),
                },
            )
        if method.startswith("prompts/"):
            return rpc_error(request_id, -32601, "Method not found")
        return rpc_error(request_id, -32601, "Method not found")

    return router
