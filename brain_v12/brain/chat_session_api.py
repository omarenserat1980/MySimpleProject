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

def router(brain_ai, store=None):
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

    @r.post("/sessions/{session_id}/messages")
    def send_message(session_id: str, body: MessageIn):
        if store.get(session_id) is None:
            return {"ok": False, "status": "SESSION_NOT_FOUND"}
        store.add_message(session_id, "user", body.message)
        result = brain_ai.chat(body.message, body.instructions, approved=body.approved)
        assistant = {"role":"assistant","content":result.reply,"ok":result.ok,"mode":result.mode,
                     "model":result.model,"tool_calls":result.tool_calls,
                     "evidence":result.evidence,"error":result.error}
        session = store.add_message(session_id, "assistant", result.reply, assistant)
        return {"ok": result.ok, "session": session, "response": assistant}
    return r
