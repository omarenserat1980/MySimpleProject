"""Conservative, evidence-based goal verifiers for Brain V12.

These verifiers intentionally cover only narrow read-only outcomes. They must not
infer that a repair, deployment, code change, or broad user goal succeeded merely
because an internal tool returned successfully.
"""
import re
import unicodedata


VERIFIER_ID = "builtin:read-only-goal-verifier-v1"


def _normalize(text):
    value = unicodedata.normalize("NFKC", str(text or "")).lower()
    value = re.sub(r"[\u064B-\u065F\u0670\u0640]", "", value)
    return re.sub(r"\s+", " ", value).strip()


def _unverified(reason):
    return {"verified": False, "evidence": "", "verifier": VERIFIER_ID, "reason": reason}


def verify_cognitive_goal(goal, execution, tool_result):
    """Verify a small allowlist of read-only goals using structured tool output."""
    if not isinstance(execution, dict) or not isinstance(tool_result, dict):
        return _unverified("MISSING_STRUCTURED_RESULT")
    if tool_result.get("ok") is not True:
        return _unverified("TOOL_RESULT_NOT_OK")

    normalized = _normalize(goal)
    if not normalized:
        return _unverified("EMPTY_GOAL")

    mutation_terms = (
        "fix", "repair", "deploy", "create", "write", "update", "change",
        "delete", "improve", "build", "solve", "execute", "implement",
        "اصلح", "إصلاح", "اصلاح", "نشر", "انشئ", "أنشئ", "اكتب",
        "عدل", "تعديل", "طور", "تطوير", "تحسين", "ابن", "احذف", "نفذ",
    )
    if any(term in normalized for term in mutation_terms):
        return _unverified("MUTATING_OR_BROAD_GOAL_NOT_COVERED")

    read_terms = (
        "read", "show", "list", "inspect", "check", "view", "status",
        "اعرض", "اقرا", "اقرأ", "افحص", "راجع", "استعرض", "تحقق",
        "اعرف", "حالة", "وضع",
    )
    has_read_intent = any(term in normalized for term in read_terms)
    tool_id = str(execution.get("tool") or tool_result.get("tool") or "")
    data = tool_result.get("data")

    status_terms = ("status", "state", "health", "حالة", "وضع", "جاهزية")
    asks_status = any(term in normalized for term in status_terms)
    if tool_id == "state.read" and isinstance(data, dict) and asks_status:
        status = data.get("status")
        if has_read_intent and status not in (None, ""):
            safe_status = str(status)[:100]
            return {
                "verified": True,
                "evidence": f"state.read returned a non-empty status field: {safe_status!r}",
                "verifier": VERIFIER_ID,
                "reason": "READ_ONLY_STATUS_FIELD_PRESENT",
            }
        return _unverified("STATUS_EVIDENCE_OR_READ_INTENT_MISSING")

    memory_terms = ("memory", "memories", "ذاكرة", "الذاكره", "الذاكرة", "ذكريات", "سجل")
    asks_memory_listing = any(term in normalized for term in memory_terms)
    if tool_id == "memory.read" and isinstance(data, list) and asks_memory_listing and has_read_intent:
        return {
            "verified": True,
            "evidence": f"memory.read returned a structured list containing {len(data)} record(s)",
            "verifier": VERIFIER_ID,
            "reason": "READ_ONLY_MEMORY_LIST_RETURNED",
        }

    return _unverified("NO_MATCHING_READ_ONLY_VERIFIER")
