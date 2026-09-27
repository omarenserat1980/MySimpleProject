"""Factuality gate for scientific, documentary and religious productions."""
from __future__ import annotations
from typing import Any

FACTUAL_GENRES = {"scientific", "documentary", "religious"}

def evaluate_research_gate(shot: dict[str, Any], result: dict[str, Any], ledger: dict[str, Any] | None = None) -> dict[str, Any]:
    ledger = ledger or {}
    genre = str(shot.get("genre") or shot.get("creative_contract", {}).get("genre") or "cinematic").lower()
    factuality = str(shot.get("factuality") or shot.get("creative_contract", {}).get("factuality") or "creative")
    required = genre in FACTUAL_GENRES or factuality in {"factual", "verified", "documentary"}
    claims = ledger.get("claims") or []
    unresolved = [c for c in claims if str(c.get("status", "")).upper() not in {"VERIFIED", "SUPPORTED"}]
    if not required:
        return {"status": "VERIFIED", "required": False, "unresolved": [], "checks": {"factuality": True}}
    dramatization = bool(shot.get("dramatization") or shot.get("creative_contract", {}).get("dramatization"))
    if dramatization:
        return {"status": "VERIFIED", "required": True, "dramatization": True,
                "unresolved": unresolved, "checks": {"factuality": True}}
    status = "VERIFIED" if not unresolved else "REPAIR"
    return {"status": status, "required": True, "dramatization": False,
            "unresolved": unresolved, "checks": {"factuality": not unresolved}}
