"""Adaptive speed policy for Electronic Brain Cinema Factory.

The policy is metadata-only: it never lowers the film QC threshold. It chooses
faster inference paths where the selected backend supports them and controls
parallelism without oversubscribing a worker.
"""
from __future__ import annotations

import os
from typing import Any


def truthy(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def speed_policy() -> dict[str, Any]:
    mode = os.getenv("FACTORY_SPEED_MODE", "max").strip().lower()
    if mode not in {"quality", "balanced", "max"}:
        mode = "max"
    requested = max(1, int(os.getenv("FACTORY_RENDER_CONCURRENCY", "3")))
    # More workers help only when the backend is remote or has multiple GPUs.
    # Keep a bounded ceiling to avoid API/GPU thrashing.
    ceiling = max(1, min(8, int(os.getenv("FACTORY_MAX_CONCURRENCY", "8"))))
    concurrency = min(requested, ceiling)
    if mode == "quality":
        profile = "production"
    elif mode == "balanced":
        profile = "fast_production"
    else:
        profile = "maximum_throughput"
    return {
        "mode": mode,
        "profile": profile,
        "concurrency": concurrency,
        "distilled_ltx": mode in {"balanced", "max"},
        "lightning_wan": mode == "max",
        "fp8": mode in {"balanced", "max"},
        "attention_optimization": mode in {"balanced", "max"},
        "reuse_loaded_models": True,
        "overlap_pipeline_stages": True,
        "adaptive_retries": True,
        "skip_verified": True,
    }


def apply_speed_policy(shot: dict[str, Any]) -> dict[str, Any]:
    policy = speed_policy()
    enriched = dict(shot)
    enriched["speed_policy"] = policy
    family = str(enriched.get("model_family") or "").lower()
    generation = dict(enriched.get("generation") or {})
    if family == "ltx":
        generation["inference_profile"] = "distilled" if policy["distilled_ltx"] else "production"
        generation["sampling_steps"] = 8 if policy["distilled_ltx"] else 20
        generation["quantization"] = "fp8" if policy["fp8"] else "bf16"
    elif family == "wan":
        generation["inference_profile"] = "lightning" if policy["lightning_wan"] else "production"
        generation["sampling_steps"] = 4 if policy["lightning_wan"] else 20
        generation["attention"] = "flash-attention" if policy["attention_optimization"] else "default"
    else:
        generation["inference_profile"] = policy["profile"]
    enriched["generation"] = generation
    enriched["reuse_reference_cache"] = True
    enriched["reuse_model_cache"] = True
    return enriched
