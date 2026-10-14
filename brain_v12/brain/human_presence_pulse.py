"""Persistent, bounded HUMAN_PRESENCE pulse stored in Brain's canonical MemoryStore.

This pulse records a one-shot evaluation when the avatar UI polls. It does not create a
background worker and never claims that a browser actually rendered a frame.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

MEMORY_KEY = "brain.pulse.HUMAN_PRESENCE"
MIN_TICK_INTERVAL_SECONDS = 60


def _now(now=None):
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def load_pulse(store):
    """Load the pulse from canonical persistent memory without creating side effects."""
    rows = store.memories()
    row = next((item for item in rows if item.get("key") == MEMORY_KEY), None)
    if not row:
        return {
            "pulse_id": "HUMAN_PRESENCE",
            "pulse_type": "HUMAN_PRESENCE",
            "schema_version": 1,
            "enabled": True,
            "tick_sequence": 0,
            "intensity": 0.0,
            "confidence": 0.0,
            "last_tick_at": None,
            "next_tick_at": None,
            "display_targets": [],
            "visual_state": "PENDING_DISPLAY_TARGET",
            "last_render_status": "PENDING_DISPLAY_TARGET",
            "user_consent_status": "enabled_for_brain_avatar_ui",
            "asset_provenance": "local_css_avatar",
            "last_outcome": "not_evaluated",
        }
    try:
        state = json.loads(row.get("value", "{}"))
        if not isinstance(state, dict) or state.get("pulse_id") != "HUMAN_PRESENCE":
            raise ValueError("invalid pulse state")
        return state
    except (TypeError, ValueError, json.JSONDecodeError):
        # Malformed saved state fails closed; do not overwrite it implicitly.
        return {
            "pulse_id": "HUMAN_PRESENCE",
            "pulse_type": "HUMAN_PRESENCE",
            "schema_version": 1,
            "enabled": False,
            "tick_sequence": 0,
            "intensity": 0.0,
            "confidence": 0.0,
            "last_tick_at": None,
            "next_tick_at": None,
            "display_targets": [],
            "visual_state": "UNCERTAIN",
            "last_render_status": "INVALID_PERSISTED_STATE",
            "user_consent_status": "disabled_until_reconfigured",
            "asset_provenance": "local_css_avatar",
            "last_outcome": "invalid_persisted_state",
        }


def evaluate_pulse(store, *, display_target="brain-avatar-ui", now=None):
    """Perform a single bounded pulse tick; the caller must be the authorized avatar UI route."""
    instant = _now(now)
    state = load_pulse(store)
    if not state.get("enabled", False):
        state["visual_state"] = "DISABLED"
        state["last_outcome"] = "pulse_disabled"
        return state

    last = state.get("last_tick_at")
    if last:
        try:
            previous = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
            if previous.tzinfo is None:
                previous = previous.replace(tzinfo=timezone.utc)
            elapsed = (instant - previous.astimezone(timezone.utc)).total_seconds()
            if elapsed < MIN_TICK_INTERVAL_SECONDS:
                return state
        except (TypeError, ValueError):
            # Invalid timestamps cause one safe refresh tick, not a false success.
            pass

    targets = state.get("display_targets", [])
    if not isinstance(targets, list):
        targets = []
    if display_target and display_target not in targets:
        targets.append(str(display_target)[:80])
    state.update({
        "pulse_id": "HUMAN_PRESENCE",
        "pulse_type": "HUMAN_PRESENCE",
        "schema_version": 1,
        "enabled": True,
        "tick_sequence": int(state.get("tick_sequence", 0)) + 1,
        "intensity": 0.25,
        "confidence": 0.5,
        "last_tick_at": instant.isoformat(),
        "next_tick_at": (instant.replace(microsecond=0) + __import__("datetime").timedelta(seconds=MIN_TICK_INTERVAL_SECONDS)).isoformat(),
        "display_targets": targets,
        "visual_state": "PENDING_RENDER_CONFIRMATION",
        "last_render_status": "API_POLLED_RENDER_NOT_INDEPENDENTLY_VERIFIED",
        "user_consent_status": "enabled_for_brain_avatar_ui",
        "asset_provenance": "local_css_avatar",
        "last_outcome": "bounded_ui_poll_tick_only",
    })
    store.save_memory(MEMORY_KEY, json.dumps(state, ensure_ascii=False, sort_keys=True))
    return state
