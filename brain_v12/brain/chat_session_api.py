"""Browser-first persistent conversation API for Brain AI."""
from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel, Field
from .chat_session_store import ChatSessionStore

class SessionCreateIn(BaseModel):
    title: str = "New Brain Chat"

class MessageIn(BaseModel):
    message: str = Field(min_length=1)
    instructions: str = ""
    approved: bool = False

class MemoryIn(BaseModel):
    summary: str = ""

def router(brain_ai, store=None, context_limit=24):
    store = store or ChatSessionStore()
    store.init()
    r = APIRouter(prefix="/api/brain-chat", tags=["Brain Chat"])

    @r.post("/sessions")
    def create_session(body: SessionCreateIn = SessionCreateIn()):
        return {"ok": True, "session": store.create(body.title)}

    @r.get("/sessions")
    def list_sessions():
        return {"ok": True, "sessions": store.list()}

    @r.get("/sessions/{session_id}")
    def get_session(session_id: str):
        session = store.get(session_id)
        if session is None:
            return {"ok": False, "status": "SESSION_NOT_FOUND"}
        return {"ok": True, "session": session}

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

    @r.post("/sessions/{session_id}/messages")
    def send_message(session_id: str, body: MessageIn):
        if store.get(session_id) is None:
            return {"ok": False, "status": "SESSION_NOT_FOUND"}
        store.add_message(session_id, "user", body.message)
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
        assistant = {"role":"assistant","content":result.reply,"ok":result.ok,"mode":result.mode,
                     "model":result.model,"tool_calls":result.tool_calls,
                     "evidence":result.evidence,"error":result.error}
        session = store.add_message(session_id, "assistant", result.reply, assistant)
        return {"ok": result.ok, "session": session, "response": assistant}
    return r
