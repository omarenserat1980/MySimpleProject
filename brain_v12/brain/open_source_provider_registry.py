from __future__ import annotations

"""Open-source provider registry for Brain's model/tool execution fabric.

This registry is metadata-only: it never downloads weights, starts processes,
or bypasses policy. Runtime adapters must be selected by the existing
Capability Resolver / Executor Router and remain single-flight.

The entries intentionally distinguish origin from license so Brain can make
policy decisions without treating "open source" as a blanket license claim.
"""

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class OpenSourceProvider:
    provider_id: str
    origin: str
    project: str
    repository: str
    capabilities: tuple[str, ...]
    code_license: str
    model_license_note: str
    local_first: bool = True


PROVIDERS: Final[dict[str, OpenSourceProvider]] = {
    "india.ai4bharat.indictrans2": OpenSourceProvider(
        provider_id="india.ai4bharat.indictrans2",
        origin="india",
        project="IndicTrans2",
        repository="https://github.com/AI4Bharat/IndicTrans2",
        capabilities=("translation", "indic-languages"),
        code_license="open-source",
        model_license_note="Model checkpoints are MIT; datasets/artifacts have separate licenses.",
    ),
    "india.ai4bharat.indicf5": OpenSourceProvider(
        provider_id="india.ai4bharat.indicf5",
        origin="india",
        project="IndicF5",
        repository="https://github.com/AI4Bharat/IndicF5",
        capabilities=("tts", "indic-languages"),
        code_license="open-source",
        model_license_note="Verify the current repository/model terms before production redistribution.",
    ),
    "china.qwen.qwen3": OpenSourceProvider(
        provider_id="china.qwen.qwen3",
        origin="china",
        project="Qwen3",
        repository="https://github.com/QwenLM/Qwen3",
        capabilities=("llm", "reasoning", "tool-use"),
        code_license="Apache-2.0",
        model_license_note="Qwen3 open-weight models are Apache-2.0; verify the exact model artifact terms.",
    ),
    "china.deepseek.v3": OpenSourceProvider(
        provider_id="china.deepseek.v3",
        origin="china",
        project="DeepSeek-V3",
        repository="https://github.com/deepseek-ai/DeepSeek-V3",
        capabilities=("llm", "reasoning", "coding"),
        code_license="MIT",
        model_license_note="Repository code is MIT; model use is governed by the DeepSeek model license.",
    ),
    "china.openbmb.minicpm": OpenSourceProvider(
        provider_id="china.openbmb.minicpm",
        origin="china",
        project="MiniCPM",
        repository="https://github.com/OpenBMB/MiniCPM",
        capabilities=("llm", "on-device", "vision"),
        code_license="Apache-2.0",
        model_license_note="Repository and MiniCPM models are Apache-2.0 according to the project.",
    ),
}


def get_provider(provider_id: str) -> OpenSourceProvider:
    try:
        return PROVIDERS[provider_id]
    except KeyError as exc:
        raise KeyError(f"UNKNOWN_OPEN_SOURCE_PROVIDER:{provider_id}") from exc


def list_providers(*, origin: str | None = None, capability: str | None = None) -> tuple[OpenSourceProvider, ...]:
    items = tuple(PROVIDERS.values())
    if origin:
        items = tuple(p for p in items if p.origin == origin)
    if capability:
        items = tuple(p for p in items if capability in p.capabilities)
    return items


def assert_allowed_for_runtime(provider_id: str, *, approved_origins: set[str], capability: str) -> OpenSourceProvider:
    provider = get_provider(provider_id)
    if provider.origin not in approved_origins:
        raise RuntimeError(f"OPEN_SOURCE_ORIGIN_NOT_APPROVED:{provider.origin}")
    if capability not in provider.capabilities:
        raise RuntimeError(f"PROVIDER_CAPABILITY_MISMATCH:{provider_id}:{capability}")
    return provider
