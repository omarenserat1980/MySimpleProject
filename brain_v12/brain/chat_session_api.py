"""Browser-first conversation/session API for Brain AI."""

from __future__ import annotations
from typing import Dict, List
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel, Field


class SessionCreateIn(BaseModel):
    title: str = "New Brain Chat"


class MessageIn(BaseModel):
    message: str = Field(min_length=1)
    instructions: str = ""
    approved: bool = False


_SESSIONS: Dict[str, Dict] = {}


def router(brain_ai):
    r = APIRouter(prefix="/api/brain-chat", tags=["Brain Chat"])

    @r.post("/sessions")
    def create_session(body: SessionCreateIn = SessionCreateIn()):
        sid = str(uuid4())
        _SESSIONS[sid] = {"id": sid, "title": body.title, "messages": []}
        return {"ok": True, "session": _SESSIONS[sid]}

    @r.get("/sessions")
    def list_sessions():
        return {"ok": True, "sessions": list(_SESSIONS.values())}

    @r.get("/sessions/{session_id}")
    def get_session(session_id: str):
        session = _SESSIONS.get(session_id)
        if session is None:
            return {"ok": False, "status": "SESSION_NOT_FOUND"}
        return {"ok": True, "session": session}

    @r.post("/sessions/{session_id}/messages")
    def send_message(session_id: str, body: MessageIn):
        session = _SESSIONS.get(session_id)
        if session is None:
            return {"ok": False, "status": "SESSION_NOT_FOUND"}
        session["messages"].append({"role": "user", "content": body.message})
        result = brain_ai.chat(body.message, body.instructions, approved=body.approved)
        assistant = {
            "role": "assistant",
            "content": result.reply,
            "ok": result.ok,
            "mode": result.mode,
            "model": result.model,
            "tool_calls": result.tool_calls,
            "evidence": result.evidence,
            "error": result.error,
        }
        session["messages"].append(assistant)
        return {"ok": result.ok, "session": session, "response": assistant}

    return r
