"""Browser-first persistent conversation API for Brain AI."""
from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel, Field
from .chat_session_store import ChatSessionStore
from .chat_request_ledger import ChatRequestLedger
from .brain_card_preflight import run_chat_preflight, stable_chat_trace_id
import hashlib
import json


class SessionCreateIn(BaseModel):
    title: str = "New Brain Chat"
    account_id: str | None = None
    device_id: str | None = None


class MessageIn(BaseModel):
    message: str = Field(min_length=1)
    instructions: str = ""
    approved: bool = False
    client_message_id: str | None = None
    device_id: str | None = None
    partner_mode: bool = False


class MemoryIn(BaseModel):
    summary: str = ""


class CompactIn(BaseModel):
    keep_recent: int = 24
    max_summary_chars: int = 12000


def router(brain_ai, store=None, context_limit=24):
    store = store or ChatSessionStore()
    store.init()
    ledger = ChatRequestLedger(store.path)
    ledger.init()
    r = APIRouter(prefix="/api/brain-chat", tags=["Brain Chat"])

    @r.post("/sessions")
    def create_session(body: SessionCreateIn = SessionCreateIn()):
        account_id = (body.account_id or "").strip() or None
        device_id = (body.device_id or "").strip() or None
        return {"ok": True, "session": store.create(body.title, account_id=account_id, device_id=device_id)}

    @r.get("/sessions")
    def list_sessions(account_id: str | None = None):
        return {"ok": True, "sessions": store.list(account_id=(account_id or "").strip() or None)}

    @r.get("/sessions/{session_id}")
    def get_session(session_id: str):
        session = store.get(session_id)
        if session is None:
            return {"ok": False, "status": "SESSION_NOT_FOUND"}
        return {"ok": True, "session": session}

    @r.get("/sessions/{session_id}/sync")
    def sync_session(session_id: str, after: int = 0, limit: int = 100, device_id: str | None = None):
        if store.get(session_id) is None:
            return {"ok": False, "status": "SESSION_NOT_FOUND"}
        feed = store.sync_events(session_id, after=after, limit=limit)
        return {"ok": True, "session_id": session_id, "device_id": device_id, **feed}

    @r.get("/sessions/{session_id}/memory")
    def get_memory(session_id: str):
        if store.get(session_id) is None:
            return {"ok": False, "status": "SESSION_NOT_FOUND"}
        return {"ok": True, "memory": store.get_memory(session_id)}

    @r.put("/sessions/{session_id}/memory")
    def set_memory(session_id: str, body: MemoryIn):
        if store.get(session_id) is None:
            return {"ok": False, "status": "SESSION_NOT_FOUND"}
        return {"ok": True, "memory": store.set_memory(session_id, body.summary)}

    @r.post("/sessions/{session_id}/compact")
    def compact_session(session_id: str, body: CompactIn = CompactIn()):
        if store.get(session_id) is None:
            return {"ok": False, "status": "SESSION_NOT_FOUND"}
        result = store.compact_session(
            session_id, keep_recent=body.keep_recent, max_summary_chars=body.max_summary_chars
        )
        return {"ok": True, "compaction": result}

    @r.post("/sessions/{session_id}/messages")
    def send_message(session_id: str, body: MessageIn):
        if store.get(session_id) is None:
            return {"ok": False, "status": "SESSION_NOT_FOUND"}

        request_key = (body.client_message_id or "").strip()
        trace_id = stable_chat_trace_id(session_id, request_key or None)

        # This gate is deliberately before idempotency recovery, message writes,
        # context/memory assembly, model calls, and tool dispatch.
        preflight = run_chat_preflight(
            brain_ai, store, r.routes, trace_id=trace_id, input_kind="chat_message"
        )
        if not preflight["ok"]:
            return {
                "ok": False,
                "status": "BRAIN_PREFLIGHT_BLOCKED",
                "trace_id": trace_id,
                "preflight": preflight,
                "response": {
                    "ok": False,
                    "status": "BRAIN_PREFLIGHT_BLOCKED",
                    "content": "Brain Card preflight failed; request processing was blocked.",
                    "trace_id": trace_id,
                },
                "idempotent_replay": False,
            }

        request_hash = hashlib.sha256(json.dumps({
            "message": body.message,
            "instructions": body.instructions,
            "approved": body.approved,
        }, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        if request_key:
            claimed = ledger.claim(session_id, request_key, request_hash)
            if claimed["status"] == "COMPLETED":
                cached = claimed["response"]
                return {"ok": bool(cached.get("ok")), "session": store.get(session_id),
                        "response": cached, "idempotent_replay": True,
                        "trace_id": trace_id, "preflight": preflight}
            if claimed["status"] == "ID_CONFLICT":
                return {"ok": False, "status": "CLIENT_MESSAGE_ID_CONFLICT", "retryable": False,
                        "trace_id": trace_id, "preflight": preflight}

            # Recover the crash window where the assistant message was persisted
            # but the idempotency ledger was not marked COMPLETED. The assistant
            # metadata carries the same client ID so retries do not call the model
            # again after a process restart.
            if claimed["status"] in ("IN_PROGRESS", "CLAIMED"):
                persisted = store.get(session_id) or {}
                recovered = next((
                    item.get("metadata", {})
                    for item in reversed(persisted.get("messages", []))
                    if item.get("role") == "assistant"
                    and item.get("metadata", {}).get("client_message_id") == request_key
                ), None)
                if recovered is not None:
                    ledger.complete(session_id, request_key, recovered)
                    return {"ok": bool(recovered.get("ok")), "session": store.get(session_id),
                            "response": recovered, "idempotent_replay": True,
                            "trace_id": trace_id, "preflight": preflight}
                if claimed["status"] == "IN_PROGRESS":
                    return {"ok": False, "status": "REQUEST_IN_PROGRESS", "retryable": True,
                            "trace_id": trace_id, "preflight": preflight}

        try:
            store.add_message(
                session_id, "user", body.message,
                client_message_id=body.client_message_id,
                metadata={
                    **({"device_id": body.device_id} if body.device_id else {}),
                    "trace_id": trace_id,
                    "brain_card_version": preflight["brain_card"]["registry_version"],
                },
            )
            history = store.context_messages(session_id, limit=context_limit)
            memory = store.get_memory(session_id)
            context_lines = ["[{}] {}".format(item["role"], item["content"]) for item in history]
            session_context = "\n".join(context_lines)
            instructions = body.instructions
            if body.partner_mode:
                from .brain_partner import PARTNER_INSTRUCTIONS
                instructions = (instructions + "\\n\\n" if instructions else "") + PARTNER_INSTRUCTIONS
            if memory and memory.get("summary"):
                instructions = (instructions + "\n\n" if instructions else "") + "[BRAIN_SESSION_MEMORY]\n" + memory["summary"]
            if session_context:
                instructions = (instructions + "\n\n" if instructions else "") + "[BRAIN_SESSION_CONTEXT]\n" + session_context
            result = brain_ai.chat(body.message, instructions, approved=body.approved)
            model_routing = next((e for e in result.evidence if e.get("type") == "model_routing"), None)
            assistant = {
                "role": "assistant", "content": result.reply, "ok": result.ok, "mode": result.mode,
                "model": result.model, "tool_calls": result.tool_calls,
                "evidence": result.evidence, "model_routing": model_routing, "error": result.error,
                "trace_id": trace_id, "brain_card_version": preflight["brain_card"]["registry_version"],
                "preflight_status": preflight["status"],
            }
            if request_key:
                assistant["client_message_id"] = request_key
            store.add_message(session_id, "assistant", result.reply, assistant)
            if request_key:
                ledger.complete(session_id, request_key, assistant)
            return {"ok": result.ok, "session": store.get(session_id), "response": assistant,
                    "idempotent_replay": False, "trace_id": trace_id, "preflight": preflight}
        except Exception:
            if request_key:
                ledger.fail(session_id, request_key)
            raise
    return r
