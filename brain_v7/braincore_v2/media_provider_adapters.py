"""Provider adapters for real image/audio/video generation.

Secrets and provider SDK clients are injected by the deployment. This module
contains no API keys and does not assume a particular vendor.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Mapping


@dataclass(frozen=True)
class ProviderResult:
    status: str
    provider: str
    provider_job_id: str | None = None
    output: Any = None
    error: str | None = None


class MediaProviderClient(Protocol):
    def submit(self, *, kind: str, prompt: str, output_format: str,
               options: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        ...

    def status(self, *, kind: str, provider_job_id: str) -> Mapping[str, Any]:
        ...


class RealMediaProviderAdapter:
    """Normalize an authenticated provider client to the brain contract."""

    def __init__(self, provider: str, client: MediaProviderClient) -> None:
        if not provider.strip():
            raise ValueError("PROVIDER_NAME_REQUIRED")
        if client is None:
            raise ValueError("AUTHENTICATED_MEDIA_CLIENT_REQUIRED")
        self.provider = provider.strip()
        self.client = client

    def submit(
        self,
        *,
        kind: str,
        prompt: str,
        output_format: str,
        options: Mapping[str, Any] | None = None,
    ) -> ProviderResult:
        result = self.client.submit(
            kind=kind,
            prompt=prompt,
            output_format=output_format,
            options=options or {},
        )
        job_id = str(result.get("job_id") or result.get("id") or "").strip()
        status = str(result.get("status") or "SUBMITTED").upper()
        if not job_id:
            return ProviderResult(
                status="FAILED",
                provider=self.provider,
                error="PROVIDER_JOB_ID_MISSING",
            )
        return ProviderResult(
            status=status,
            provider=self.provider,
            provider_job_id=job_id,
            output=result.get("output"),
            error=result.get("error"),
        )

    def status(self, *, kind: str, provider_job_id: str) -> ProviderResult:
        job_id = str(provider_job_id).strip()
        if not job_id:
            raise ValueError("PROVIDER_JOB_ID_REQUIRED")
        result = self.client.status(kind=kind, provider_job_id=job_id)
        status = str(result.get("status") or "PENDING").upper()
        return ProviderResult(
            status=status,
            provider=self.provider,
            provider_job_id=job_id,
            output=result.get("output"),
            error=result.get("error"),
        )


def provider_capabilities(
    providers: Mapping[str, RealMediaProviderAdapter],
) -> dict[str, list[str]]:
    """Report configured provider names without exposing credentials."""
    return {
        "providers": sorted(providers),
        "capability_types": ["image", "audio", "video", "design"],
    }
