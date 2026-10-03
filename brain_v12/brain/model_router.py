from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ModelProvider:
    name: str
    handler: Callable[..., Dict[str, Any]]
    tasks: List[str]
    priority: int = 100
    enabled: bool = True


class ModelRouter:
    """Deterministic provider router with explicit fallback and audit evidence."""

    DEFAULT_TASKS = ("chat", "reasoning", "coding", "vision", "creative", "summarization")

    def __init__(self, default_model: Optional[str] = None, fallback_models: Optional[List[str]] = None):
        self.providers: Dict[str, ModelProvider] = {}
        self.default_model = default_model or os.getenv("BRAIN_MODEL_DEFAULT", "")
        env_fallbacks = os.getenv("BRAIN_MODEL_FALLBACKS", "")
        self.fallback_models = list(fallback_models or [x.strip() for x in env_fallbacks.split(",") if x.strip()])

    def register(self, name, handler, tasks=None, priority=100, enabled=True):
        self.providers[name] = ModelProvider(name, handler, list(tasks or self.DEFAULT_TASKS), int(priority), bool(enabled))
        return self.providers[name]

    def disable(self, name):
        if name in self.providers:
            self.providers[name].enabled = False

    def enabled(self, task="chat"):
        candidates = [p for p in self.providers.values() if p.enabled and (task in p.tasks or "*" in p.tasks)]
        candidates.sort(key=lambda p: (p.priority, p.name))
        return [p.name for p in candidates]

    def select(self, task="chat", preferred=None):
        available = self.enabled(task)
        ordered = []
        for name in [preferred, self.default_model, *self.fallback_models]:
            if name and name in available and name not in ordered:
                ordered.append(name)
        ordered.extend(name for name in available if name not in ordered)
        if not ordered:
            return {"ok": False, "status": "NO_MODEL_AVAILABLE", "task": task, "candidates": available}
        return {"ok": True, "status": "MODEL_SELECTED", "task": task, "model": ordered[0],
                "fallbacks": ordered[1:], "candidates": available}

    def route(self, task, payload, preferred=None):
        selection = self.select(task, preferred)
        if not selection["ok"]:
            return selection
        attempts = []
        ordered = [selection["model"], *selection["fallbacks"]]
        for index, name in enumerate(ordered):
            provider = self.providers[name]
            try:
                result = provider.handler(payload)
                if isinstance(result, dict) and result.get("ok", True):
                    return {
                        "ok": True, "status": "MODEL_COMPLETED", "model": name, "task": task,
                        "result": result.get("result", result),
                        "attempts": attempts + [{"model": name, "ok": True}],
                        "fallback_used": index > 0,
                        "evidence": {
                            "type": "model_routing",
                            "task": task,
                            "selected": name,
                            "preferred": preferred,
                            "candidates": selection["candidates"],
                            "attempts": attempts + [{"model": name, "ok": True}],
                            "fallback_used": index > 0,
                        },
                    }
                error = result.get("error", "MODEL_FAILED") if isinstance(result, dict) else "INVALID_MODEL_RESULT"
            except Exception as exc:
                error = str(exc)[:1000]
            attempts.append({"model": name, "ok": False, "error": error})
        return {"ok": False, "status": "ALL_MODELS_FAILED", "task": task, "attempts": attempts,
                "evidence": {"type": "model_routing", "task": task, "candidates": selection["candidates"], "attempts": attempts}}

    def respond(self, user_text, context="", instructions="", task="chat", preferred=None):
        routed = self.route(task, {"user_text": user_text, "context": context, "instructions": instructions}, preferred)
        if not routed["ok"]:
            return routed
        result = routed["result"]
        if not isinstance(result, dict):
            result = {"reply": str(result)}
        return {
            "ok": True, "provider": routed["model"], "model": result.get("model", routed["model"]),
            "reply": result.get("reply", ""), "response_id": result.get("response_id"),
            "routing": {
                "task": task, "selected_model": routed["model"],
                "fallback_used": routed["fallback_used"], "attempts": routed["attempts"],
            },
            "evidence": routed["evidence"],
        }

    def status(self):
        return {
            "ok": True, "default_model": self.default_model or None,
            "fallback_models": self.fallback_models,
            "providers": [{"name": p.name, "tasks": p.tasks, "priority": p.priority, "enabled": p.enabled}
                         for p in sorted(self.providers.values(), key=lambda x: (x.priority, x.name))],
        }
