"""Runtime registry and router for injected multimedia providers."""
from __future__ import annotations

from typing import Any, Mapping

from .media_provider_adapters import RealMediaProviderAdapter


class MediaProviderRegistry:
    def __init__(self, providers: Mapping[str, RealMediaProviderAdapter] | None = None):
        self.providers = dict(providers or {})

    def register(self, name: str, adapter: RealMediaProviderAdapter) -> None:
        key = name.strip()
        if not key:
            raise ValueError("PROVIDER_NAME_REQUIRED")
        self.providers[key] = adapter

    def available(self, kind: str | None = None) -> list[str]:
        return sorted(self.providers)

    def choose(self, kind: str, preferred: str | None = None) -> RealMediaProviderAdapter | None:
        if preferred and preferred in self.providers:
            return self.providers[preferred]
        return next(iter(self.providers.values()), None)

    def submit(
        self,
        *,
        kind: str,
        prompt: str,
        output_format: str,
        preferred: str | None = None,
        options: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        provider = self.choose(kind, preferred)
        if provider is None:
            return {
                "status": "NO_PROVIDER",
                "kind": kind,
                "reason": "MEDIA_PROVIDER_NOT_CONNECTED",
            }
        result = provider.submit(
            kind=kind,
            prompt=prompt,
            output_format=output_format,
            options=options,
        )
        return {
            "status": result.status,
            "provider": result.provider,
            "provider_job_id": result.provider_job_id,
            "output": result.output,
            "error": result.error,
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "providers": sorted(self.providers),
            "provider_count": len(self.providers),
            "credentials_in_registry": False,
        }
