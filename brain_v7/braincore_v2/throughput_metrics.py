"""Persistent, provider-neutral stage timing for verified throughput decisions.

Records warmup and steady-state latency without changing quality thresholds.
The data is advisory: missing or corrupt telemetry never blocks production.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

DEFAULT_PATH = ".factory_throughput.json"


def telemetry_path(path: str | Path | None = None) -> Path:
    return Path(path or os.getenv("FACTORY_THROUGHPUT_PATH", DEFAULT_PATH))


def load(path: str | Path | None = None) -> dict[str, Any]:
    target = telemetry_path(path)
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("stages"), dict):
            return data
    except (OSError, ValueError, TypeError):
        pass
    return {"version": 1, "stages": {}, "updated_at": 0.0}


def _save(data: dict[str, Any], path: str | Path | None = None) -> None:
    target = telemetry_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    data = dict(data)
    data["updated_at"] = time.time()
    fd, tmp = tempfile.mkstemp(prefix=".factory-throughput-", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(tmp, target)
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass


def record(
    stage: str,
    elapsed_s: float,
    *,
    success: bool = True,
    warmup: bool = False,
    path: str | Path | None = None,
) -> dict[str, Any]:
    data = load(path)
    item = data.setdefault("stages", {}).setdefault(stage, {
        "samples": 0, "successes": 0, "failures": 0,
        "warmup_samples": 0, "steady_samples": 0,
        "ewma_latency_s": None, "ewma_steady_latency_s": None,
    })
    item["samples"] += 1
    item["successes"] += int(success)
    item["failures"] += int(not success)
    item["warmup_samples"] += int(warmup)
    item["steady_samples"] += int(not warmup)
    alpha = 0.35
    item["ewma_latency_s"] = (
        float(elapsed_s) if item["ewma_latency_s"] is None
        else alpha * float(elapsed_s) + (1 - alpha) * float(item["ewma_latency_s"])
    )
    if not warmup:
        item["ewma_steady_latency_s"] = (
            float(elapsed_s) if item["ewma_steady_latency_s"] is None
            else alpha * float(elapsed_s) + (1 - alpha) * float(item["ewma_steady_latency_s"])
        )
    _save(data, path)
    return item


@contextmanager
def measure(
    stage: str,
    *,
    warmup: bool = False,
    path: str | Path | None = None,
) -> Iterator[dict[str, Any]]:
    started = time.monotonic()
    meta = {"stage": stage, "warmup": warmup, "success": False}
    try:
        yield meta
    except Exception:
        meta["elapsed_s"] = round(time.monotonic() - started, 6)
        record(stage, meta["elapsed_s"], success=False, warmup=warmup, path=path)
        raise
    else:
        meta["elapsed_s"] = round(time.monotonic() - started, 6)
        meta["success"] = True
        record(stage, meta["elapsed_s"], success=True, warmup=warmup, path=path)


def snapshot(path: str | Path | None = None) -> dict[str, Any]:
    data = load(path)
    return {
        "version": data.get("version", 1),
        "stages": data.get("stages", {}),
        "updated_at": data.get("updated_at", 0.0),
    }
