#!/usr/bin/env python3
"""ChatGPT reasoning bridge for the Brain reflection loop.

ChatGPT may recommend an allowlisted action, but it never receives direct shell access.
"""
from __future__ import annotations

import json
import re
from typing import Mapping, Any

from brain_v12.brain.openai_provider import OpenAIProvider


class ChatGPTReasoner:
    """Turn Brain questions + evidence into a validated action recommendation."""

    def __init__(self, provider: OpenAIProvider | None = None) -> None:
        self.provider = provider or OpenAIProvider()

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any] | None:
        text = text.strip()
        try:
            value = json.loads(text)
            return value if isinstance(value, dict) else None
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if not match:
                return None
            try:
                value = json.loads(match.group(0))
                return value if isinstance(value, dict) else None
            except json.JSONDecodeError:
                return None

    def plan(self, question: str, context: Mapping[str, object]) -> dict[str, Any]:
        allowed = list(context.get("allowed_actions", []))
        descriptions = dict(context.get("action_descriptions", {}))
        action_catalog = {
            action_id: descriptions.get(action_id, "")
            for action_id in allowed
        }
        prompt = (
            "The Brain is running a bounded self-reflection cycle.\n"
            f"Question: {question}\n"
            f"Observed evidence/context: {json.dumps(dict(context), ensure_ascii=False, default=str)}\n"
            f"Allowed action catalog: {json.dumps(action_catalog, ensure_ascii=False)}\n\n"
            "Return ONLY JSON with keys: answer, action_id, reason, expected_evidence, risk. "
            "action_id MUST be one of the supplied allowed action IDs or 'none'. "
            "Never invent commands, shell text, URLs, credentials, or new action IDs."
        )
        result = self.provider.respond(
            prompt,
            instructions=(
                "You are the planning layer of Electronic Brain. "
                "Give a concise operational answer. Do not execute anything. "
                "Return only the requested JSON object."
            ),
        )
        if not result.get("ok"):
            return {
                "ok": False,
                "answer": "",
                "action_id": "none",
                "reason": result.get("error", "REASONER_FAILED"),
                "expected_evidence": [],
                "risk": "unknown",
            }

        plan = self._extract_json(result.get("reply", ""))
        if not plan:
            return {
                "ok": False,
                "answer": result.get("reply", ""),
                "action_id": "none",
                "reason": "INVALID_PLANNER_JSON",
                "expected_evidence": [],
                "risk": "unknown",
            }

        action_id = plan.get("action_id", "none")
        if action_id not in allowed and action_id != "none":
            action_id = "none"
        return {
            "ok": True,
            "answer": str(plan.get("answer", "")),
            "action_id": action_id,
            "reason": str(plan.get("reason", "")),
            "expected_evidence": plan.get("expected_evidence", []),
            "risk": str(plan.get("risk", "unknown")),
        }

    def choose_action(self, question: str, context: Mapping[str, object]) -> str:
        return str(self.plan(question, context).get("action_id", "none"))
