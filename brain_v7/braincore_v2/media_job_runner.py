"""Bounded media job runner.

Submits provider jobs, polls them to terminal state, and verifies that a
usable output reference exists before a stage is considered complete.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
import time

from .media_provider_registry import MediaProviderRegistry


TERMINAL = {"COMPLETED", "SUCCEEDED", "FAILED", "CANCELLED", "TIMED_OUT"}


@dataclass(frozen=True)
class JobResult:
    status: str
    provider: str | None = None
    provider_job_id: str | None = None
    output: Any = None
    error: str | None = None


def _has_output(output: Any) -> bool:
    if isinstance(output, str):
        return bool(output.strip())
    if isinstance(output, Mapping):
        return any(
            isinstance(output.get(key), str) and output.get(key).strip()
            for key in ("url", "path", "uri", "file", "output")
        )
    return output is not None


class MediaJobRunner:
    def __init__(self, registry: MediaProviderRegistry):
        self.registry = registry

    def run(
        self,
        *,
        kind: str,
        prompt: str,
        output_format: str,
        preferred: str | None = None,
        options: Mapping[str, Any] | None = None,
        authorized: bool = False,
        timeout_seconds: int = 3600,
        poll_seconds: int = 5,
    ) -> dict[str, Any]:
        if not authorized:
            return {"status": "AUTHORIZATION_REQUIRED", "kind": kind}

        submitted = self.registry.submit(
            kind=kind,
            prompt=prompt,
            output_format=output_format,
            preferred=preferred,
            options=options,
        )
        status = str(submitted.get("status", "")).upper()
        if status in {"NO_PROVIDER", "FAILED"}:
            return submitted

        provider_name = submitted.get("provider")
        job_id = submitted.get("provider_job_id")
        output = submitted.get("output")

        if _has_output(output) and status in {"COMPLETED", "SUCCEEDED"}:
            return {**submitted, "status": "VERIFIED_COMPLETED"}

        if not provider_name or not job_id:
            return {
                **submitted,
                "status": "FAILED",
                "error": "PROVIDER_JOB_REFERENCE_REQUIRED",
            }

        provider = self.registry.providers.get(provider_name)
        if provider is None:
            return {
                **submitted,
                "status": "FAILED",
                "error": "PROVIDER_NOT_FOUND",
            }

        deadline = time.time() + max(1, timeout_seconds)
        while time.time() < deadline:
            try:
                current = provider.status(kind=kind, provider_job_id=str(job_id))
            except Exception as exc:
                return {
                    **submitted,
                    "status": "FAILED",
                    "error": str(exc),
                }

            current_status = str(current.status).upper()
            if current_status in TERMINAL:
                if current_status in {"COMPLETED", "SUCCEEDED"} and _has_output(current.output):
                    return {
                        "status": "VERIFIED_COMPLETED",
                        "provider": current.provider,
                        "provider_job_id": current.provider_job_id,
                        "output": current.output,
                    }
                return {
                    "status": current_status,
                    "provider": current.provider,
                    "provider_job_id": current.provider_job_id,
                    "output": current.output,
                    "error": current.error or "PROVIDER_DID_NOT_RETURN_USABLE_OUTPUT",
                }
            time.sleep(max(1, poll_seconds))

        return {
            **submitted,
            "status": "TIMEOUT",
            "provider": provider_name,
            "provider_job_id": job_id,
        }
