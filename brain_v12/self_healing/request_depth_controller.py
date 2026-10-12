"""Adaptive request-driven depth policy for Electronic Brain.

Depth grows from real user requests and accumulated capability, not from a
prebuilt catalog of scripts/apps. Each request can justify exactly the new
capability it needs; unused capabilities are not created.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DepthDecision:
    request_number: int
    previous_depth: int
    depth: int
    reason: str
    required_capabilities: tuple[str, ...]
    create_capabilities: tuple[str, ...]


class RequestDepthController:
    schema = "brain-request-depth/v1"

    CAPABILITY_RULES = (
        ("script", ("script", "سكربت", "automation", "أتمت")),
        ("api", ("api", "endpoint", "واجهة")),
        ("app", ("app", "application", "تطبيق")),
        ("adapter", ("adapter", "connector", "موصل", "ربط")),
        ("diagnostics", ("debug", "diagnostic", "تشخيص", "عالج", "حل")),
        ("cloud", ("azure", "cloud", "سحابي", "vm", "container")),
        ("media", ("video", "movie", "فيديو", "فيلم", "media")),
        ("agent", ("agent", "عميل", "وكيل")),
    )

    def __init__(self, state_path: str | Path = ".brain/state/request_depth.json"):
        self.path = Path(state_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema": self.schema, "request_number": 0, "depth": 0,
                    "capabilities": {}, "history": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"schema": self.schema, "request_number": 0, "depth": 0,
                    "capabilities": {}, "history": []}

    def classify(self, request: str) -> tuple[str, ...]:
        text = request.lower()
        found = []
        for name, terms in self.CAPABILITY_RULES:
            if any(term.lower() in text for term in terms):
                found.append(name)
        return tuple(found)

    def decide(self, request: str) -> DepthDecision:
        state = self._load()
        number = int(state.get("request_number", 0)) + 1
        previous = int(state.get("depth", 0))
        required = self.classify(request)

        # Every meaningful new user request advances the Brain depth by one.
        # Additional depth is earned only when the request introduces a new
        # capability that the Brain does not yet possess.
        depth = previous + 1
        existing = state.get("capabilities", {})
        create = tuple(x for x in required if x not in existing)

        reason = "new_user_request"
        if create:
            reason += "+new_capability:" + ",".join(create)

        return DepthDecision(number, previous, depth, reason, required, create)

    def commit(self, request: str, decision: DepthDecision) -> dict[str, Any]:
        state = self._load()
        state["schema"] = self.schema
        state["request_number"] = decision.request_number
        state["depth"] = decision.depth

        for capability in decision.required_capabilities:
            state.setdefault("capabilities", {})[capability] = {
                "first_request": decision.request_number,
                "status": "required",
            }

        state.setdefault("history", []).append({
            "request_number": decision.request_number,
            "timestamp": time.time(),
            "request": request[:2000],
            "previous_depth": decision.previous_depth,
            "depth": decision.depth,
            "reason": decision.reason,
            "required_capabilities": list(decision.required_capabilities),
            "create_capabilities": list(decision.create_capabilities),
        })
        # Keep the ledger bounded; the durable depth/capability state remains.
        state["history"] = state["history"][-100:]
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)
        return state
