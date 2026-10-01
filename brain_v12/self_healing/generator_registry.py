"""Explicit registry for native Brain improvement generators.

Unknown candidate types are never generator-eligible. Adding a new type requires
an explicit registry entry and its own tests before it can mutate source.
"""
from __future__ import annotations

SUPPORTED_GENERATORS = {
    "package-invocation-consistency": {
        "module": "brain_v12.self_healing.native_patch_generator",
        "risk": "low",
        "roots": ("brain_v12/", "tests/", "scripts/"),
    },
}


def is_supported(candidate_id: str) -> bool:
    return candidate_id in SUPPORTED_GENERATORS


def supported_candidates(candidates: list[dict]) -> list[dict]:
    return [c for c in candidates if is_supported(str(c.get("id", "")))]
