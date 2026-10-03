from fastapi import APIRouter
from pydantic import BaseModel


class BrainAIChatIn(BaseModel):
    message: str
    instructions: str = ""


class BrainAIToolIn(BaseModel):
    name: str
    params: dict = {}
    approved: bool = False


def router(brain_ai):
    r = APIRouter(prefix="/api/brain-ai", tags=["Brain AI"])

    @r.get("/status")
    def status():
        return {"ok": True, **brain_ai.status()}

    @r.post("/chat")
    def chat(body: BrainAIChatIn):
        result = brain_ai.chat(body.message, body.instructions)
        return {"ok": result.ok, "reply": result.reply, "mode": result.mode,
                "model": result.model, "tool_calls": result.tool_calls,
                "evidence": result.evidence, "error": result.error}

    @r.post("/tool")
    def tool(body: BrainAIToolIn):
        return brain_ai.execute_tool(body.name, body.params, body.approved)

    return r
