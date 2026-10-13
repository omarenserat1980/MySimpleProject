from uuid import uuid4
from fastapi import APIRouter
from pydantic import BaseModel
from .brain_gpt_20_layer_runtime import build_layer_runtime_status
from .brain_card_preflight import run_chat_preflight


class BrainAIChatIn(BaseModel):
    message: str
    instructions: str = ""
    approved: bool = False


class BrainAIToolIn(BaseModel):
    name: str
    params: dict = {}
    approved: bool = False


def router(brain_ai, session_store=None):
    r = APIRouter(prefix="/api/brain-ai", tags=["Brain AI"])

    @r.get("/status")
    def status():
        return {"ok": True, **brain_ai.status()}

    @r.get("/layers/status")
    def layers_status():
        return build_layer_runtime_status(brain_ai, session_store)

    @r.post("/chat")
    def chat(body: BrainAIChatIn):
        trace_id = "brain-ai-" + uuid4().hex[:20]
        preflight = run_chat_preflight(
            brain_ai, session_store, r.routes,
            trace_id=trace_id, input_kind="brain_ai_chat",
        )
        if not preflight["ok"]:
            return {
                "ok": False, "status": "BRAIN_PREFLIGHT_BLOCKED",
                "trace_id": trace_id, "preflight": preflight,
                "error": "Brain Card preflight failed; AI processing was blocked.",
            }
        result = brain_ai.chat(body.message, body.instructions, approved=body.approved)
        return {"ok": result.ok, "reply": result.reply, "mode": result.mode,
                "model": result.model, "tool_calls": result.tool_calls,
                "evidence": result.evidence, "error": result.error,
                "trace_id": trace_id, "preflight": preflight,
                "brain_card_version": preflight["brain_card"]["registry_version"],
                "model_routing": next((e for e in result.evidence if e.get("type") == "model_routing"), None)}

    @r.post("/tool")
    def tool(body: BrainAIToolIn):
        trace_id = "brain-tool-" + uuid4().hex[:20]
        preflight = run_chat_preflight(
            brain_ai, session_store, r.routes,
            trace_id=trace_id, input_kind="brain_ai_tool",
        )
        if not preflight["ok"]:
            return {
                "ok": False, "status": "BRAIN_PREFLIGHT_BLOCKED",
                "trace_id": trace_id, "preflight": preflight,
                "error": "Brain Card preflight failed; tool dispatch was blocked.",
            }
        result = brain_ai.execute_tool(body.name, body.params, body.approved)
        return {**result, "trace_id": trace_id, "preflight": preflight,
                "brain_card_version": preflight["brain_card"]["registry_version"]}

    return r
