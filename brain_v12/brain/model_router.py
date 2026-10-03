from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

@dataclass
class ModelRoute:
    provider: Any
    provider_name: str
    model: Optional[str]
    reason: str

class ModelRouter:
    """Provider registry and deterministic fallback router for Brain AI."""
    def __init__(self, default_provider=None):
        self.providers: Dict[str, Any] = {}
        self.capabilities: Dict[str, set[str]] = {}
        self.default_provider_name: Optional[str] = None
        if default_provider is not None:
            name = self._provider_name(default_provider)
            self.register(name, default_provider, default=True)

    @staticmethod
    def _provider_name(provider) -> str:
        status = provider.status() if hasattr(provider, "status") else {}
        return str(status.get("provider") or getattr(provider, "name", None) or provider.__class__.__name__).lower()

    def register(self, name: str, provider, capabilities=None, default: bool = False):
        key = str(name).strip().lower()
        if not key:
            raise ValueError("PROVIDER_NAME_REQUIRED")
        self.providers[key] = provider
        self.capabilities[key] = {str(x).lower() for x in (capabilities or [])}
        if default or self.default_provider_name is None:
            self.default_provider_name = key

    def status(self) -> Dict[str, Any]:
        return {"default": self.default_provider_name, "providers": [{"name": n, "capabilities": sorted(self.capabilities.get(n, set())), "status": p.status() if hasattr(p, "status") else {}} for n, p in self.providers.items()]}

    def route(self, user_text: str, requested_capability: Optional[str] = None) -> ModelRoute:
        text = (user_text or "").lower()
        capability = (requested_capability or "").lower().strip()
        if not capability and any(x in text for x in ("صورة", "صوّر", "image", "vision", "صوت", "audio", "ملف", "file")):
            capability = "multimodal"
        if capability:
            for name, caps in self.capabilities.items():
                if capability in caps:
                    p = self.providers[name]
                    return ModelRoute(p, name, self._model(p), "capability:" + capability)
        if not self.default_provider_name or self.default_provider_name not in self.providers:
            raise RuntimeError("NO_MODEL_PROVIDER")
        p = self.providers[self.default_provider_name]
        return ModelRoute(p, self.default_provider_name, self._model(p), "default")

    @staticmethod
    def _model(provider):
        status = provider.status() if hasattr(provider, "status") else {}
        return status.get("model") or getattr(provider, "model", None)

    def respond(self, user_text: str, context: str = "", instructions: str = "", requested_capability: Optional[str] = None) -> Dict[str, Any]:
        route = self.route(user_text, requested_capability)
        ordered = [route.provider_name] + [n for n in self.providers if n != route.provider_name]
        errors = []
        for name in ordered:
            try:
                result = self.providers[name].respond(user_text, context=context, instructions=instructions)
            except Exception as exc:
                errors.append({"provider": name, "error": str(exc)[:500]})
                continue
            if result.get("ok"):
                result = dict(result)
                result.setdefault("provider", name)
                result["route_reason"] = route.reason if name == route.provider_name else "fallback"
                if errors:
                    result["fallback_errors"] = errors
                return result
            errors.append({"provider": name, "error": result.get("error", "PROVIDER_FAILED")})
        return {"ok": False, "error": "ALL_MODEL_PROVIDERS_FAILED", "route_reason": route.reason, "provider_errors": errors}
