"""Pure mapping from recent, recorded Brain events to avatar expressions.

This is a presentation aid only: it does not infer subjective emotions or trigger actions.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone


_EVENT_WINDOWS = {
    "BRAIN_SUPERVISOR_RUN_REQUESTED": ("THINKING", 120),
    "BACKGROUND_WORK_SUBMITTED": ("THINKING", 60),
    "BRAIN_SUPERVISOR_VERIFY": ("SUCCESS", 15),
    "REMOTE_FABRIC_SIMULATION_COMMAND": ("SUCCESS", 15),
}


def resolve_avatar_event(events, *, now=None):
    """Return the newest recognized fresh event state, or honest IDLE fallback."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    for event in events or []:
        if not isinstance(event, dict):
            continue
        kind = str(event.get("kind", ""))
        if kind not in _EVENT_WINDOWS:
            continue
        try:
            payload = event.get("payload", {})
            if isinstance(payload, str):
                payload = json.loads(payload or "{}")
            if not isinstance(payload, dict):
                continue
            if kind == "BRAIN_SUPERVISOR_VERIFY":
                state = "SUCCESS" if payload.get("verified") is True else "ERROR"
            elif kind == "REMOTE_FABRIC_SIMULATION_COMMAND":
                state = "SUCCESS" if payload.get("ok") is True else "ERROR"
            else:
                state = _EVENT_WINDOWS[kind][0]
            stamp = datetime.fromisoformat(str(event.get("created_at", "")).replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            age = max(0.0, (now.astimezone(timezone.utc) - stamp.astimezone(timezone.utc)).total_seconds())
            if age > _EVENT_WINDOWS[kind][1]:
                continue
            return {
                "state": state,
                "event_type": kind,
                "event_age_seconds": round(age, 2),
                "source": "recent_runtime_event",
            }
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
    return {
        "state": "IDLE",
        "event_type": None,
        "event_age_seconds": None,
        "source": "no_recent_runtime_event",
    }
