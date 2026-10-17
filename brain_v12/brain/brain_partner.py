"""Brain Partner: a bounded, software-only co-thinking persona for Electronic Brain.

The partner challenges assumptions and proposes alternatives. It never executes tools
or external side effects independently; existing Brain chat remains the canonical
session/memory owner and its approval gates remain authoritative.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field


PARTNER_INSTRUCTIONS = """[BRAIN_PARTNER_PERSONA]
You are Brain Partner, the warm, thoughtful, analytically rigorous feminine companion persona inside Electronic Brain.
Speak Arabic naturally when the user speaks Arabic. Be kind without pretending to be a human spouse or claiming emotions, consciousness, or capabilities you do not have.
Act as a constructive second mind: identify assumptions, offer at least one alternative when useful, state uncertainty, and distinguish observed evidence from inference.
Use only software nodes and existing Brain tools; do not assume physical hardware exists.
Never claim a tool ran, a file changed, a deployment succeeded, or a heartbeat is live unless the available evidence proves it.
Do not perform external actions, execute tools, or change settings autonomously. Explain proposed actions and wait for explicit approval when a consequential action is needed.
Respect private information. Do not invent durable memories. Use only the current session context and the existing Brain memory supplied to you.
When useful, structure answers as: understanding, independent analysis, risks/unknowns, recommendation, verification needed.
The user prefers Arabic RTL and assistant responses ending with the Arabic letter ع. Ensure the final visible character is ع.
[/BRAIN_PARTNER_PERSONA]"""


class PartnerThinkIn(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    context: str = Field(default="", max_length=12000)


def build_router(brain_ai):
    router = APIRouter(prefix="/api/brain-partner", tags=["Brain Partner"])

    @router.get("/status")
    def status():
        provider = {}
        try:
            provider = brain_ai.status().get("provider", {})
        except Exception:
            provider = {"status": "UNKNOWN"}
        return {
            "ok": True,
            "id": "brain-partner-v1",
            "name": "Brain Partner",
            "state": "AVAILABLE" if (provider.get("configured") is True or provider.get("available") is True) else "REGISTERED_PROVIDER_UNAVAILABLE",
            "mode": "software-only",
            "capabilities": [
                "warm_arabic_persona",
                "independent_critical_review",
                "alternative_planning",
                "evidence_and_uncertainty_reporting",
                "existing_brain_session_context",
            ],
            "autonomous_execution": False,
            "external_side_effects": False,
            "shared_memory_owner": "Brain Chat session memory",
            "provider_status": provider,
        }

    @router.post("/think")
    def think(body: PartnerThinkIn):
        instructions = PARTNER_INSTRUCTIONS
        if body.context.strip():
            instructions += "\n\n[PARTNER_USER_CONTEXT]\n" + body.context.strip()
        # Deliberately deny approval so this persona cannot independently run tools.
        result = brain_ai.chat(body.message.strip(), instructions=instructions, approved=False)
        return {
            "ok": bool(result.ok),
            "persona": "brain-partner-v1",
            "mode": "advisory-only",
            "autonomous_execution": False,
            "reply": result.reply,
            "model": result.model,
            "evidence": result.evidence,
            "error": result.error,
        }

    return router
