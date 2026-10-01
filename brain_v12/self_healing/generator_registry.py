"""Explicit contracts for native Brain improvement generators.

Unknown candidate types are never generator-eligible. Every supported generator
declares its implementation module, allowed source roots, required verification
actions, and risk level.
"""
from __future__ import annotations

SUPPORTED_GENERATORS = {
    "package-invocation-consistency": {
        "module": "brain_v12.self_healing.native_patch_generator",
        "risk": "low",
        "roots": ("brain_v12/", "tests/", "scripts/"),
        "max_changed_files": 1,
        "verification": ("compile", "self-test", "tests", "gate"),
    },
}


def contract(candidate_id: str) -> dict | None:
    return SUPPORTED_GENERATORS.get(candidate_id)


def is_supported(candidate_id: str) -> bool:
    return contract(candidate_id) is not None


def supported_candidates(candidates: list[dict]) -> list[dict]:
    return [c for c in candidates if is_supported(str(c.get("id", "")))]


def path_allowed(path: str, candidate_id: str) -> bool:
    item = contract(candidate_id)
    if not item:
        return False
    normalized = path.replace("\\", "/")
    if normalized.split("/")[-1].startswith("test_"):
        return False
    if normalized.startswith("/") or ".." in normalized.split("/"):
        return False
    return any(normalized == root.rstrip("/") or normalized.startswith(root) for root in item["roots"])


def candidate_valid(candidate: dict) -> bool:
    candidate_id = str(candidate.get("id", ""))
    target = str(candidate.get("file", ""))
    return bool(candidate_id and path_allowed(target, candidate_id))
