#!/usr/bin/env python3
"""Choose an Electronic Brain execution channel without spending fallback quotas.

This module is a deterministic routing policy. It does not execute remote work:
callers must provide fresh evidence for each channel and then invoke the selected
Brain-owned adapter. Unknown/unobserved channels are unavailable by default.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

PRIORITY = (
    "brain_local",
    "github_actions_arkan",
    "termux_agent",
    "desktop_commander",
)


def choose_execution_channel(evidence: dict[str, Any]) -> dict[str, Any]:
    """Select the highest-priority available channel from explicit evidence.

    Each channel is eligible only when its evidence entry has available=true.
    Desktop Commander additionally requires quota_available=true, so an
    exhausted quota can never be selected accidentally.
    """
    channels = evidence.get("channels", {})
    if not isinstance(channels, dict):
        channels = {}
    for name in PRIORITY:
        item = channels.get(name)
        if not isinstance(item, dict) or item.get("available") is not True:
            continue
        if name == "desktop_commander" and item.get("quota_available") is not True:
            continue
        return {
            "ok": True,
            "selected": name,
            "priority": list(PRIORITY),
            "reason": str(item.get("reason") or "fresh availability evidence supplied"),
            "execution_performed": False,
            "requires_adapter_execution": True,
        }
    return {
        "ok": False,
        "selected": None,
        "priority": list(PRIORITY),
        "reason": "NO_VERIFIED_EXECUTION_CHANNEL",
        "execution_performed": False,
        "requires_adapter_execution": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", help="JSON file containing fresh channel availability evidence; reads stdin if omitted")
    args = parser.parse_args()
    try:
        raw = open(args.evidence, encoding="utf-8").read() if args.evidence else sys.stdin.read()
        evidence = json.loads(raw or "{}")
        if not isinstance(evidence, dict):
            raise ValueError("evidence must be a JSON object")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": "INVALID_EVIDENCE", "detail": str(exc)}))
        return 2
    result = choose_execution_channel(evidence)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
