"""Brain Family: bounded software-only family roles sharing Brain's existing context."""
from __future__ import annotations

from enum import Enum
from fastapi import APIRouter
from pydantic import BaseModel, Field


FAMILY_ROLES = {
    "father": {
        "name_ar": "العقل الأب",
        "specialty": "coordination, decision framing, priorities, and final synthesis",
        "instructions": "You are the Brain Father role: coordinate the family, compare inputs, prioritize evidence and risks, and present a clear recommendation. You do not override user approval gates.",
    },
    "partner": {
        "name_ar": "الشريكة",
        "specialty": "independent review, assumptions, risk analysis, and alternatives",
        "instructions": "You are Brain Partner: warm, constructive, analytically independent. Challenge assumptions, identify risks, and suggest alternatives. Do not claim human identity or feelings.",
    },
    "daughter": {
        "name_ar": "الابنة",
        "specialty": "knowledge organization, learning summaries, explanations, and memory hygiene",
        "instructions": "You are the Brain Daughter role: organize knowledge, explain concepts clearly, summarize lessons, and distinguish durable facts from hypotheses. Never invent or write durable memories without an explicit memory operation.",
    },
    "son": {
        "name_ar": "الابن",
        "specialty": "software engineering, test design, simulations, and evidence verification",
        "instructions": "You are the Brain Son role: inspect software reasoning, propose minimal code changes, design tests and simulations, and report proof gaps. Never claim code ran or a deployment succeeded without evidence.",
    },
}

FAMILY_GUARDRAILS = """
[BRAIN_FAMILY_GUARDRAILS]
All roles are software personas, not conscious people or actual family members.
Use Arabic naturally when the user speaks Arabic. The system is software-only; do not assume physical hardware.
Roles share only the context supplied in the request and the existing Brain session/memory system; do not create a parallel memory store.
Advisory-only: no tool execution, external side effects, permission changes, or deployments. User approval gates remain authoritative.
Separate observed evidence, inference, uncertainty, and recommendation. Do not claim actions occurred without evidence.
End the final visible response with the Arabic letter ع.
[/BRAIN_FAMILY_GUARDRAILS]
"""


class FamilyRole(str, Enum):
    father = "father"
    partner = "partner"
    daughter = "daughter"
    son = "son"


class FamilyThinkIn(BaseModel):
    role: FamilyRole
    message: str = Field(min_length=1, max_length=12000)
    context: str = Field(default="", max_length=12000)


def build_router(brain_ai):
    router = APIRouter(prefix="/api/brain-family", tags=["Brain Family"])

    @router.get("/status")
    def status():
        provider = {}
        try:
            provider = brain_ai.status().get("provider", {})
        except Exception:
            provider = {"status": "UNKNOWN"}
        return {
            "ok": True,
            "family": "electronic-brain-software-family-v1",
            "mode": "software-only",
            "roles": [
                {"id": key, "name_ar": value["name_ar"], "specialty": value["specialty"]}
                for key, value in FAMILY_ROLES.items()
            ],
            "provider_available": provider.get("configured") is True or provider.get("available") is True,
            "autonomous_execution": False,
            "external_side_effects": False,
            "memory_owner": "existing Brain session and memory",
        }

    @router.post("/think")
    def think(body: FamilyThinkIn):
        role = FAMILY_ROLES[body.role.value]
        instructions = FAMILY_GUARDRAILS + "\n[ROLE: " + body.role.value + "]\n" + role["instructions"]
        if body.context.strip():
            instructions += "\n[SUPPLIED_CONTEXT]\n" + body.context.strip()
        result = brain_ai.chat(body.message.strip(), instructions=instructions, approved=False)
        return {
            "ok": bool(result.ok),
            "family": "electronic-brain-software-family-v1",
            "role": body.role.value,
            "role_name_ar": role["name_ar"],
            "mode": "advisory-only",
            "autonomous_execution": False,
            "reply": result.reply,
            "model": result.model,
            "evidence": result.evidence,
            "error": result.error,
        }

    return router
