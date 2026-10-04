from __future__ import annotations
import hashlib, json, time
from dataclasses import dataclass, field
from typing import Any, Callable

@dataclass(frozen=True)
class FabricPolicy:
    free_first: bool = True
    max_attempts: int = 3
    require_verification: bool = True
    allow_external_side_effects: bool = False

@dataclass
class Capability:
    name: str
    kind: str
    handler: Callable[[dict[str, Any]], dict[str, Any]]
    tasks: set[str] = field(default_factory=lambda: {"*"})
    priority: int = 100
    free: bool = True
    enabled: bool = True

class AIFabric:
    """Governance layer over Brain's existing model/tool stack."""
    def __init__(self, policy: FabricPolicy | None = None):
        self.policy = policy or FabricPolicy()
        self.models, self.agents, self.tools = {}, {}, {}

    def register(self, name, kind, handler, tasks=None, priority=100, free=True):
        if kind not in {"model", "agent", "tool"}:
            raise ValueError("INVALID_CAPABILITY_KIND")
        cap = Capability(name, kind, handler, tasks or {"*"}, int(priority), bool(free))
        getattr(self, kind + "s")[name] = cap

    def _candidates(self, registry, task):
        items = [c for c in registry.values() if c.enabled and ("*" in c.tasks or task in c.tasks)]
        items.sort(key=lambda c: (not c.free, c.priority, c.name) if self.policy.free_first else (c.priority, c.name))
        return items

    @staticmethod
    def _verify(result):
        return isinstance(result, dict) and result.get("ok") is True and result.get("verified") is True

    @staticmethod
    def _evidence(task, attempts, selected=None):
        payload = {"task": task, "selected": selected, "attempts": attempts}
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode()
        return {**payload, "evidence_id": "fabric-" + hashlib.sha256(raw).hexdigest()[:20], "timestamp": time.time()}

    def execute(self, task, payload, kind="model"):
        registry = getattr(self, kind + "s", None)
        if registry is None:
            return {"ok": False, "status": "UNKNOWN_CAPABILITY_KIND", "kind": kind}
        candidates = self._candidates(registry, task)
        if not candidates:
            return {"ok": False, "status": "NO_CAPABILITY", "task": task, "kind": kind}
        attempts = []
        for cap in candidates[:max(1, self.policy.max_attempts)]:
            try:
                result = cap.handler(payload)
                verified = self._verify(result)
                attempts.append({"name": cap.name, "ok": isinstance(result, dict) and result.get("ok", False), "verified": verified})
                if isinstance(result, dict) and result.get("ok") and (not self.policy.require_verification or verified):
                    return {"ok": True, "status": "FABRIC_VERIFIED", "capability": cap.name,
                            "result": result, "evidence": self._evidence(task, attempts, cap.name)}
            except Exception as exc:
                attempts.append({"name": cap.name, "ok": False, "verified": False, "error": str(exc)[:500]})
        return {"ok": False, "status": "ALL_CAPABILITIES_FAILED", "task": task,
                "evidence": self._evidence(task, attempts), "attempts": attempts}

    def consensus(self, task, payload, min_agreement=2):
        candidates = self._candidates(self.models, task)
        if len(candidates) < min_agreement:
            return {"ok": False, "status": "INSUFFICIENT_MODELS", "available": [c.name for c in candidates]}
        results = []
        for cap in candidates[:max(min_agreement, self.policy.max_attempts)]:
            try:
                result = cap.handler(payload)
                if isinstance(result, dict) and result.get("ok"):
                    value = result.get("result", result.get("reply", result))
                    fp = hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()[:16]
                    results.append({"model": cap.name, "fingerprint": fp, "result": value, "verified": self._verify(result)})
            except Exception as exc:
                results.append({"model": cap.name, "error": str(exc)[:500], "verified": False})
        groups = {}
        for item in results:
            if "fingerprint" in item:
                groups.setdefault(item["fingerprint"], []).append(item)
        winner = max(groups.values(), key=len, default=[])
        agreed = len(winner) >= min_agreement
        attempts = [{"model": x["model"], "verified": x.get("verified", False)} for x in results]
        return {"ok": agreed, "status": "CONSENSUS_VERIFIED" if agreed else "CONSENSUS_NOT_REACHED",
                "agreement": len(winner), "results": results, "evidence": self._evidence(task, attempts)}

    def registry(self):
        def view(reg):
            return [{"name": c.name, "tasks": sorted(c.tasks), "priority": c.priority, "free": c.free, "enabled": c.enabled}
                    for c in sorted(reg.values(), key=lambda x: (x.priority, x.name))]
        return {"ok": True, "policy": self.policy.__dict__, "models": view(self.models),
                "agents": view(self.agents), "tools": view(self.tools)}
