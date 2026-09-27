"""Persistent adaptive backend benchmark for the cinema factory.

The router learns from completed shots instead of assuming a permanent global winner.
Statistics are keyed by hardware profile, shot role and backend family. A backend
can only become preferred when its observed quality stays above the factory floor.
Unknown backends remain eligible for exploration.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any


DEFAULT_PATH = ".cinema_benchmark_state.json"


def _path() -> Path:
    return Path(os.getenv("FACTORY_BENCHMARK_PATH", DEFAULT_PATH))


def _hardware_profile() -> str:
    return os.getenv("FACTORY_HARDWARE_PROFILE", "unknown").strip() or "unknown"


def _role(shot: dict[str, Any]) -> str:
    return str(shot.get("role") or shot.get("shot_type") or "unknown").strip().lower() or "unknown"


def _key(shot: dict[str, Any], family: str) -> str:
    return "|".join((_hardware_profile(), _role(shot), family.lower()))


def _empty() -> dict[str, Any]:
    return {"version": 1, "observations": {}, "updated_at": 0.0}


def load_state(path: str | Path | None = None) -> dict[str, Any]:
    target = Path(path) if path else _path()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("observations"), dict):
            return data
    except (FileNotFoundError, OSError, ValueError, TypeError):
        pass
    return _empty()


def save_state(state: dict[str, Any], path: str | Path | None = None) -> None:
    target = Path(path) if path else _path()
    target.parent.mkdir(parents=True, exist_ok=True)
    state = dict(state)
    state["updated_at"] = time.time()
    fd, tmp_name = tempfile.mkstemp(prefix=".cinema-benchmark-", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(tmp_name, target)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def _stats(state: dict[str, Any], shot: dict[str, Any], family: str) -> dict[str, Any]:
    return state.setdefault("observations", {}).setdefault(
        _key(shot, family),
        {"family": family, "samples": 0, "successes": 0, "failures": 0,
         "ewma_latency_s": None, "ewma_quality": None, "ewma_qc": None,
         "last_status": None},
    )


def record_observation(
    state: dict[str, Any],
    shot: dict[str, Any],
    family: str,
    *,
    latency_s: float,
    success: bool,
    quality_score: float | None = None,
    qc_score: float | None = None,
) -> dict[str, Any]:
    item = _stats(state, shot, family)
    item["samples"] += 1
    item["successes"] += int(success)
    item["failures"] += int(not success)
    alpha = 0.35
    item["ewma_latency_s"] = latency_s if item["ewma_latency_s"] is None else (
        alpha * latency_s + (1 - alpha) * item["ewma_latency_s"]
    )
    for field, value in (("ewma_quality", quality_score), ("ewma_qc", qc_score)):
        if value is not None:
            item[field] = value if item[field] is None else alpha * value + (1 - alpha) * item[field]
    item["last_status"] = "success" if success else "failure"
    return item


def choose_backend(
    shot: dict[str, Any],
    candidates: list[str],
    *,
    quality_floor: float = 0.82,
    state: dict[str, Any] | None = None,
) -> str:
    names = [str(x).lower() for x in candidates if x]
    if not names:
        return "fallback"
    state = state if state is not None else load_state()
    ranked: list[tuple[float, str]] = []
    for family in names:
        item = state.get("observations", {}).get(_key(shot, family), {})
        samples = int(item.get("samples", 0))
        quality = item.get("ewma_qc")
        if quality is None:
            quality = item.get("ewma_quality")
        if samples < 2:
            # Exploration: try unknown/under-sampled candidates before locking in.
            score = 1000.0 - samples
        elif quality is not None and float(quality) < quality_floor:
            score = -1000.0 + float(quality)
        else:
            latency = max(0.001, float(item.get("ewma_latency_s") or 9999.0))
            success_rate = float(item.get("successes", 0)) / max(1, samples)
            score = (1.0 / latency) * (0.5 + 0.5 * success_rate)
        ranked.append((score, family))
    ranked.sort(key=lambda pair: (-pair[0], pair[1]))
    return ranked[0][1]


def benchmark_snapshot(path: str | Path | None = None) -> dict[str, Any]:
    state = load_state(path)
    return {
        "version": state.get("version", 1),
        "hardware_profile": _hardware_profile(),
        "observations": state.get("observations", {}),
        "quality_floor": float(os.getenv("FACTORY_BENCHMARK_QUALITY_FLOOR", "0.82")),
    }
