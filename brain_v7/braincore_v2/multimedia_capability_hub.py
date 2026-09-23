"""Unified multimedia capability hub.

Provider-neutral orchestration for image, audio, video and design generation.
The hub plans and routes jobs; real provider credentials stay outside the
repository and irreversible external publication remains gated.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Callable, Mapping


@dataclass(frozen=True)
class MediaJob:
    job_id: str
    kind: str
    prompt: str
    output_format: str
    provider: str = "auto"
    status: str = "PLANNED"


SUPPORTED = {
    "image": {"png", "jpg", "webp"},
    "audio": {"mp3", "wav", "m4a"},
    "video": {"mp4", "webm", "mov"},
    "design": {"png", "pdf", "mp4"},
}


class MultimediaHub:
    """Routes media jobs to explicitly injected provider callables."""

    def __init__(self, providers: Mapping[str, Callable[..., Any]] | None = None):
        self.providers = dict(providers or {})

    def plan(self, kind: str, prompt: str, output_format: str | None = None,
             job_id: str = "media-job") -> MediaJob:
        kind = kind.lower().strip()
        if kind not in SUPPORTED:
            raise ValueError(f"Unsupported media kind: {kind}")
        fmt = (output_format or next(iter(SUPPORTED[kind]))).lower()
        if fmt not in SUPPORTED[kind]:
            raise ValueError(f"Unsupported format {fmt} for {kind}")
        if not prompt.strip():
            raise ValueError("prompt must not be empty")
        return MediaJob(job_id, kind, prompt.strip(), fmt)

    def available_providers(self, kind: str) -> list[str]:
        return sorted(self.providers)

    def execute(self, job: MediaJob, *, provider: str | None = None,
                authorized: bool = False) -> dict:
        if not authorized:
            return {"status": "AUTHORIZATION_REQUIRED", "job": asdict(job)}
        name = provider or job.provider
        if name == "auto":
            name = next(iter(self.providers), "")
        if not name or name not in self.providers:
            return {"status": "NO_PROVIDER", "job": asdict(job)}
        result = self.providers[name](job)
        return {"status": "COMPLETED", "provider": name,
                "job": asdict(job), "result": result}

    def snapshot(self) -> dict:
        return {
            "supported": {k: sorted(v) for k, v in SUPPORTED.items()},
            "providers_configured": sorted(self.providers),
            "external_publication": False,
            "credentials_in_source": False,
        }


def build_media_plan(kind: str, prompt: str, output_format: str | None = None) -> dict:
    return asdict(MultimediaHub().plan(kind, prompt, output_format))
