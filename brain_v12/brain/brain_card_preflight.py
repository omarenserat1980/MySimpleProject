"""Brain Card-backed, fail-closed preflight for Brain chat and simulator ingress.

The card is derived from the live in-process route table supplied by the owner;
it is not a claim about external hosts or deployment health.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Iterable
from uuid import uuid4
import os

BRAIN_CARD_ID = "electronic-brain-runtime"
BRAIN_CARD_VERSION = "runtime-route-contract-v1"
CHAT_MESSAGE_ROUTE = "/api/brain-chat/sessions/{session_id}/messages"
REQUIRED_CHAT_ROUTES = (
    (CHAT_MESSAGE_ROUTE, "POST", "brain-chat"),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _route_contract(routes: Iterable[Any]) -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for route in routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None) or ()
        if path:
            found.update((str(path), str(method).upper()) for method in methods)
    return found


def run_chat_preflight(
    brain_ai: Any,
    store: Any,
    routes: Iterable[Any],
    *,
    trace_id: str | None = None,
    input_kind: str = "chat_message",
) -> dict:
    """Return a sanitized Brain Card report; performs no model/tool calls."""
    trace_id = str(trace_id or ("brain-" + uuid4().hex))
    checked_at = _utc_now()
    route_set = _route_contract(routes)
    checks: list[dict] = []

    def record(check_id: str, ok: bool, target: str, evidence: str) -> None:
        checks.append({
            "check_id": check_id,
            "target_id": target,
            "status": "PASS" if ok else "FAIL",
            "evidence_ref": evidence,
        })

    for path, method, target in REQUIRED_CHAT_ROUTES:
        registered = (path, method) in route_set
        record("route.chat_message.registered", registered, target,
               "route-table:registered" if registered else "route-table:missing")

    ai_ready = callable(getattr(brain_ai, "chat", None))
    record("service.brain_ai.callable", ai_ready, "brain-ai",
           "in-process:chat-callable" if ai_ready else "in-process:chat-unavailable")

    store_ready = callable(getattr(store, "get", None)) and callable(getattr(store, "add_message", None))
    record("service.chat_store.available", store_ready, "brain-chat-store",
           "in-process:store-interface" if store_ready else "in-process:store-unavailable")

    execution_plane = os.getenv("BRAIN_EXECUTION_PLANE", "software").strip().lower()
    software_plane = execution_plane in {"software", "virtual", "simulated"}
    record("policy.software_plane", software_plane, "brain-execution-plane",
           "policy:software-plane" if software_plane else "policy:non-software-plane")

    failed = [item["check_id"] for item in checks if item["status"] != "PASS"]
    ok = not failed
    return {
        "ok": ok,
        "status": "READY" if ok else "BLOCKED",
        "trace_id": trace_id,
        "input_kind": str(input_kind),
        "brain_card": {
            "brain_id": BRAIN_CARD_ID,
            "registry_version": BRAIN_CARD_VERSION,
            "source": "live-in-process-route-table",
            "external_host_verified": False,
        },
        "checked_at": checked_at,
        "checks": checks,
        "blocked_reasons": failed,
        "execution_plane": execution_plane,
    }


def stable_chat_trace_id(session_id: str, client_message_id: str | None) -> str:
    """Stable correlation ID for retries; never contains user text or credentials."""
    key = (client_message_id or "").strip()
    if key:
        digest = sha256((str(session_id) + ":" + key).encode("utf-8")).hexdigest()[:20]
        return "chat-" + digest
    return "chat-" + uuid4().hex[:20]
