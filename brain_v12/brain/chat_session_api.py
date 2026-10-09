"""Browser-first persistent conversation API for Brain AI."""
from __future__ import annotations
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from .chat_session_store import ChatSessionStore
from .chat_identity import ChatIdentityStore
from .chat_request_ledger import ChatRequestLedger
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
    identities = ChatIdentityStore(store.path)
    identities.init()

    def require_identity(authorization):
        scheme, _, token = (authorization or "").partition(" ")
        principal = identities.authenticate(token.strip()) if scheme.lower() == "bearer" else None
        if principal is None:
            raise HTTPException(status_code=401, detail="BRAIN_CHAT_AUTH_REQUIRED")
        return principal

    def owned_session(session_id, principal):
        session = store.get(session_id)
        if session is None or session.get("account_id") != principal["account_id"]:
            raise HTTPException(status_code=404, detail="SESSION_NOT_FOUND")
        return session
    r = APIRouter(prefix="/api/brain-chat", tags=["Brain Chat"])

    @r.post("/sessions")
    def create_session(body: SessionCreateIn = SessionCreateIn(), authorization: str | None = Header(default=None)):
        principal = require_identity(authorization)
        return {"ok": True, "session": store.create(body.title, account_id=principal["account_id"], device_id=principal["device_id"])}

    @r.get("/sessions")
    def list_sessions(account_id: str | None = None, authorization: str | None = Header(default=None)):
        principal = require_identity(authorization)
        return {"ok": True, "sessions": store.list(account_id=principal["account_id"])}

    @r.get("/sessions/{session_id}")
    def get_session(session_id: str, authorization: str | None = Header(default=None)):
        principal = require_identity(authorization)
        return {"ok": True, "session": owned_session(session_id, principal)}

    @r.get("/sessions/{session_id}/sync")
    def sync_session(session_id: str, after: int = 0, limit: int = 100, device_id: str | None = None, authorization: str | None = Header(default=None)):
        principal = require_identity(authorization)
        owned_session(session_id, principal)
        feed = store.sync_events(session_id, after=after, limit=limit)
        return {"ok": True, "session_id": session_id, "device_id": principal["device_id"], **feed}

    @r.get("/sessions/{session_id}/memory")
    def get_memory(session_id: str, authorization: str | None = Header(default=None)):
        principal = require_identity(authorization)
        owned_session(session_id, principal)
        return {"ok": True, "memory": store.get_memory(session_id)}

    @r.put("/sessions/{session_id}/memory")
    def set_memory(session_id: str, body: MemoryIn, authorization: str | None = Header(default=None)):
        principal = require_identity(authorization)
        owned_session(session_id, principal)
        return {"ok": True, "memory": store.set_memory(session_id, body.summary)}

    @r.post("/sessions/{session_id}/compact")
    def compact_session(session_id: str, body: CompactIn = CompactIn(), authorization: str | None = Header(default=None)):
        principal = require_identity(authorization)
        owned_session(session_id, principal)
        result = store.compact_session(
            session_id, keep_recent=body.keep_recent, max_summary_chars=body.max_summary_chars
        )
        return {"ok": True, "compaction": result}

    @r.post("/sessions/{session_id}/messages")
    def send_message(session_id: str, body: MessageIn, authorization: str | None = Header(default=None)):
        principal = require_identity(authorization)
        owned_session(session_id, principal)

        request_key = (body.client_message_id or "").strip()
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
                        "response": cached, "idempotent_replay": True}
            if claimed["status"] == "ID_CONFLICT":
                return {"ok": False, "status": "CLIENT_MESSAGE_ID_CONFLICT", "retryable": False}

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
                            "response": recovered, "idempotent_replay": True}
                if claimed["status"] == "IN_PROGRESS":
                    return {"ok": False, "status": "REQUEST_IN_PROGRESS", "retryable": True}

        try:
            store.add_message(session_id, "user", body.message,
                              client_message_id=body.client_message_id,
                              metadata={"device_id": principal["device_id"]})
            history = store.context_messages(session_id, limit=context_limit)
            memory = store.get_memory(session_id)
            context_lines = ["[{}] {}".format(item["role"], item["content"]) for item in history]
            session_context = "\n".join(context_lines)
            instructions = body.instructions
            if memory and memory.get("summary"):
                instructions = (instructions + "\n\n" if instructions else "") + "[BRAIN_SESSION_MEMORY]\n" + memory["summary"]
            if session_context:
                instructions = (instructions + "\n\n" if instructions else "") + "[BRAIN_SESSION_CONTEXT]\n" + session_context
            result = brain_ai.chat(body.message, instructions, approved=body.approved)
            model_routing = next((e for e in result.evidence if e.get("type") == "model_routing"), None)
            assistant = {"role":"assistant","content":result.reply,"ok":result.ok,"mode":result.mode,
                         "model":result.model,"tool_calls":result.tool_calls,
                         "evidence":result.evidence,"model_routing":model_routing,"error":result.error}
            if request_key:
                assistant["client_message_id"] = request_key
            store.add_message(session_id, "assistant", result.reply, assistant)
            if request_key:
                ledger.complete(session_id, request_key, assistant)
            return {"ok": result.ok, "session": store.get(session_id), "response": assistant,
                    "idempotent_replay": False}
        except Exception:
            if request_key:
                ledger.fail(session_id, request_key)
            raise
    return r
