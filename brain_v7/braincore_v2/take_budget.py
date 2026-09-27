"""Adaptive take budget: spend extra generation only where it is likely to pay off."""
from __future__ import annotations
from typing import Any

def take_budget(shot: dict[str, Any]) -> dict[str, Any]:
    role = str((shot.get("generation") or {}).get("continuity_policy") or "")
    purpose = str(shot.get("purpose") or "").lower()
    score = 0
    if role in {"identity_first", "match_cut"}: score += 2
    if "attention" in purpose or "tension" in purpose or "hero" in purpose: score += 2
    if float(shot.get("duration_s", 0) or 0) >= 5: score += 1
    max_takes = 1 if score <= 1 else 2 if score <= 3 else 3
    return {
        "max_takes": max_takes,
        "strategy": "early_accept",
        "generate_next_only_after_qc_failure": True,
    }
