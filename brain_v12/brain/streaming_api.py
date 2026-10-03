from __future__ import annotations

import json
from typing import Iterator, Callable, Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field


class StreamMessageIn(BaseModel):
    message: str = Field(min_length=1)
    instructions: str = ""
    approved: bool = False


def _sse(event: str, data: dict) -> str:
    return "event: " + event + "\ndata: " + json.dumps(data, ensure_ascii=False) + "\n\n"


def iter_text(text: str, chunk_size: int = 32) -> Iterator[str]:
    for i in range(0, len(text), max(1, chunk_size)):
        yield text[i:i + max(1, chunk_size)]


def stream_result(result: Any, chunk_size: int = 32) -> Iterator[str]:
    if isinstance(result, dict) and result.get("ok") is False:
        yield _sse("error", result)
        yield _sse("done", {"ok": False})
        return
    reply = getattr(result, "reply", None)
    if reply is None and isinstance(result, dict):
        reply = result.get("reply", "")
    reply = str(reply or "")
    meta = {
        "ok": bool(getattr(result, "ok", result.get("ok", True) if isinstance(result, dict) else True)),
        "model": getattr(result, "model", result.get("model") if isinstance(result, dict) else None),
    }
    yield _sse("start", meta)
    for chunk in iter_text(reply, chunk_size):
        yield _sse("delta", {"text": chunk})
    yield _sse("done", {"ok": meta["ok"], "model": meta["model"]})


def router(brain_ai, store=None, context_limit=24):
    r = APIRouter(prefix="/api/brain-stream", tags=["Brain Streaming"])

    @r.get("/capabilities")
    def capabilities():
        return {"ok": True, "protocol": "SSE", "events": ["start", "delta", "error", "done"], "chunked": True}

    @r.post("/chat")
    def chat(body: StreamMessageIn):
        def generate():
            result = brain_ai.chat(body.message, body.instructions, approved=body.approved)
            yield from stream_result(result)
        return StreamingResponse(generate(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    return r
