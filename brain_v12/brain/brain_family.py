"""Brain Family: bounded software-only roles with durable memory in Brain's existing store."""
from __future__ import annotations

import json
from enum import Enum
from fastapi import APIRouter
from pydantic import BaseModel, Field


FAMILY_ROLES = {
    "father": {
        "name_ar": "العقل الأب",
        "specialty": "coordination, decision framing, priorities, and final synthesis",
        "instructions": "You are the Brain Father role: coordinate the family, compare inputs, prioritize evidence and risks, and present a clear recommendation. You do not override user approval gates.",
        "memory_seed": {"purpose": "coordination", "rules": ["evidence first", "software-only", "approval gates remain authoritative"], "lessons": []},
    },
    "partner": {
        "name_ar": "الشريكة",
        "specialty": "independent review, assumptions, risk analysis, and alternatives",
        "instructions": "You are Brain Partner: warm, constructive, analytically independent. Challenge assumptions, identify risks, and suggest alternatives. Do not claim human identity or feelings.",
        "memory_seed": {"purpose": "independent review", "rules": ["separate evidence from inference", "state uncertainty", "no autonomous actions"], "lessons": []},
    },
    "daughter": {
        "name_ar": "الابنة",
        "specialty": "knowledge organization, learning summaries, explanations, and memory hygiene",
        "instructions": "You are the Brain Daughter role: organize knowledge, explain concepts clearly, summarize lessons, and distinguish durable facts from hypotheses. Never invent or write durable memories without an explicit memory operation.",
        "memory_seed": {"purpose": "knowledge organization and learning", "rules": ["do not invent memories", "label hypotheses", "preserve useful lessons"], "lessons": []},
    },
    "son": {
        "name_ar": "الابن",
        "specialty": "software engineering, test design, simulations, and evidence verification",
        "instructions": "You are the Brain Son role: inspect software reasoning, propose minimal code changes, design tests and simulations, and report proof gaps. Never claim code ran or a deployment succeeded without evidence.",
        "memory_seed": {"purpose": "software engineering and verification", "rules": ["test before claiming success", "minimal changes", "no hardware assumptions"], "lessons": []},
    },
}

FAMILY_GUARDRAILS = """
[BRAIN_FAMILY_GUARDRAILS]
All roles are software personas, not conscious people or actual family members.
Use Arabic naturally when the user speaks Arabic. The system is software-only; do not assume physical hardware.
Use each role's durable notes from the existing Brain MemoryStore when supplied; do not create a parallel memory database.
Advisory-only: no tool execution, external side effects, permission changes, or deployments. User approval gates remain authoritative.
Separate observed evidence, inference, uncertainty, and recommendation. Do not claim actions occurred without evidence.
End the final visible response with the Arabic letter ع.
[/BRAIN_FAMILY_GUARDRAILS]
"""

MEMORY_PREFIX = "brain_family:v1:"


class FamilyRole(str, Enum):
    father = "father"
    partner = "partner"
    daughter = "daughter"
    son = "son"


class FamilyThinkIn(BaseModel):
    role: FamilyRole
    message: str = Field(min_length=1, max_length=12000)
    context: str = Field(default="", max_length=12000)


def _read_role_memory(memory_store, role_id):
    if memory_store is None:
        return None
    try:
        for item in memory_store.memories():
            if item.get("key") == MEMORY_PREFIX + role_id:
                try:
                    return json.loads(item.get("value", "{}"))
                except (TypeError, ValueError):
                    return {"status": "MEMORY_PARSE_ERROR"}
    except Exception:
        return {"status": "MEMORY_READ_ERROR"}
    return None


def restore_missing_family_memories(memory_store):
    """Restore only missing role records; never overwrite any existing memory."""
    if memory_store is None:
        return {"ok": False, "status": "MEMORY_STORE_UNAVAILABLE", "restored": [], "preserved": []}
    restored, preserved, errors = [], [], []
    for role_id, role in FAMILY_ROLES.items():
        key = MEMORY_PREFIX + role_id
        try:
            current = _read_role_memory(memory_store, role_id)
            if current is not None:
                preserved.append(role_id)
                continue
            value = json.dumps({
                "schema": "brain-family-memory-v1",
                "role": role_id,
                "name_ar": role["name_ar"],
                "purpose": role["memory_seed"]["purpose"],
                "rules": role["memory_seed"]["rules"],
                "lessons": role["memory_seed"]["lessons"],
                "restored_from": "versioned_role_seed",
            }, ensure_ascii=False)
            memory_store.save_memory(key, value)
            restored.append(role_id)
        except Exception as exc:
            errors.append({"role": role_id, "error": str(exc)[:200]})
    return {"ok": not errors, "status": "RESTORED" if not errors else "PARTIAL", "restored": restored, "preserved": preserved, "errors": errors}


def build_router(brain_ai, memory_store=None):
    router = APIRouter(prefix="/api/brain-family", tags=["Brain Family"])

    @router.get("/status")
    def status():
        provider = {}
        try:
            provider = brain_ai.status().get("provider", {})
        except Exception:
            provider = {"status": "UNKNOWN"}
        role_rows = []
        for key, value in FAMILY_ROLES.items():
            saved = _read_role_memory(memory_store, key)
            role_rows.append({
                "id": key,
                "name_ar": value["name_ar"],
                "specialty": value["specialty"],
                "memory": "AVAILABLE" if saved is not None and "status" not in saved else "MISSING",
            })
        return {
            "ok": True,
            "family": "electronic-brain-software-family-v1",
            "mode": "software-only",
            "roles": role_rows,
            "provider_available": provider.get("configured") is True or provider.get("available") is True,
            "autonomous_execution": False,
            "external_side_effects": False,
            "memory_owner": "existing Brain MemoryStore",
        }

    @router.get("/memory")
    def family_memory_status():
        return {
            "ok": True,
            "memory_owner": "existing Brain MemoryStore",
            "roles": {role_id: _read_role_memory(memory_store, role_id) for role_id in FAMILY_ROLES},
        }

    @router.post("/memory/restore")
    def restore_memory():
        return restore_missing_family_memories(memory_store)

    @router.post("/think")
    def think(body: FamilyThinkIn):
        role_id = body.role.value
        role = FAMILY_ROLES[role_id]
        saved_memory = _read_role_memory(memory_store, role_id)
        instructions = FAMILY_GUARDRAILS + "\n[ROLE: " + role_id + "]\n" + role["instructions"]
        if saved_memory is not None:
            instructions += "\n[ROLE_DURABLE_MEMORY]\n" + json.dumps(saved_memory, ensure_ascii=False)
        if body.context.strip():
            instructions += "\n[SUPPLIED_CONTEXT]\n" + body.context.strip()
        result = brain_ai.chat(body.message.strip(), instructions=instructions, approved=False)
        return {
            "ok": bool(result.ok),
            "family": "electronic-brain-software-family-v1",
            "role": role_id,
            "role_name_ar": role["name_ar"],
            "memory_loaded": saved_memory is not None,
            "mode": "advisory-only",
            "autonomous_execution": False,
            "reply": result.reply,
            "model": result.model,
            "evidence": result.evidence,
            "error": result.error,
        }

    return router
