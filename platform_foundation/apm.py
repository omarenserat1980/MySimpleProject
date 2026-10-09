from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from .persistent_state import SQLiteStateStore


@dataclass(frozen=True)
class MetricPoint:
    metric: str
    metric_type: str
    value: float
    timestamp: float
    dimensions: dict[str, str] = field(default_factory=dict)
    task_id: str | None = None
    run_id: str | None = None
    commit_sha: str | None = None
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)


class APM:
    """Durable, evidence-first application performance monitoring.

    APM records measurements and derives health; it never treats missing telemetry
    as healthy. Dimensions are bounded to avoid unbounded-cardinality storage.
    """

    STATE_KEY = "platform.apm.metrics"

    def __init__(
        self,
        store: SQLiteStateStore,
        *,
        clock: Callable[[], float] = time.time,
        max_series: int = 1000,
        max_dimensions: int = 8,
        max_dimension_length: int = 128,
    ) -> None:
        if max_series < 1 or max_dimensions < 1 or max_dimension_length < 1:
            raise ValueError("APM limits must be positive")
        self.store = store
        self.clock = clock
        self.max_series = max_series
        self.max_dimensions = max_dimensions
        self.max_dimension_length = max_dimension_length

    @staticmethod
    def _validate_metric(metric: str) -> str:
        if not isinstance(metric, str) or not metric.strip():
            raise ValueError("metric is required")
        metric = metric.strip()
        if len(metric) > 128:
            raise ValueError("metric is too long")
        return metric

    def _validate_dimensions(self, dimensions: Mapping[str, str] | None) -> dict[str, str]:
        dimensions = {} if dimensions is None else dict(dimensions)
        if len(dimensions) > self.max_dimensions:
            raise ValueError("too many metric dimensions")
        clean: dict[str, str] = {}
        for key, value in dimensions.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError("dimension key is required")
            if not isinstance(value, str):
                raise TypeError("dimension values must be strings")
            if len(key) > self.max_dimension_length or len(value) > self.max_dimension_length:
                raise ValueError("dimension is too long")
            clean[key.strip()] = value
        return dict(sorted(clean.items()))

    @staticmethod
    def _context(value: str | None, name: str) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string")
        if len(value) > 256:
            raise ValueError(f"{name} is too long")
        return value.strip()

    @staticmethod
    def _series_key(metric: str, dimensions: dict[str, str]) -> str:
        import json
        return metric + "|" + json.dumps(dimensions, sort_keys=True, separators=(",", ":"))

    def record(
        self,
        metric: str,
        value: float,
        *,
        metric_type: str = "gauge",
        dimensions: Mapping[str, str] | None = None,
        task_id: str | None = None,
        run_id: str | None = None,
        commit_sha: str | None = None,
    ) -> MetricPoint:
        metric = self._validate_metric(metric)
        if metric_type not in {"counter", "gauge", "histogram"}:
            raise ValueError("unsupported metric type")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError("metric value must be numeric")
        value = float(value)
        if metric_type == "counter" and value < 0:
            raise ValueError("counter increments cannot be negative")
        dimensions = self._validate_dimensions(dimensions)
        task_id = self._context(task_id, "task_id")
        run_id = self._context(run_id, "run_id")
        commit_sha = self._context(commit_sha, "commit_sha")
        point = MetricPoint(
            metric=metric,
            metric_type=metric_type,
            value=value,
            timestamp=float(self.clock()),
            dimensions=dimensions,
            task_id=task_id,
            run_id=run_id,
            commit_sha=commit_sha,
        )
        key = self._series_key(metric, dimensions)

        def update(current: Any) -> tuple[bool, Any]:
            state = {} if current is None else dict(current)
            if key not in state and len(state) >= self.max_series:
                raise RuntimeError("APM series cardinality limit reached")
            old = state.get(key)
            if old is None:
                if metric_type == "counter":
                    aggregate = {"count": 1, "sum": value, "last": value}
                elif metric_type == "histogram":
                    aggregate = {"count": 1, "sum": value, "min": value, "max": value, "last": value}
                else:
                    aggregate = {"count": 1, "last": value}
            else:
                if old["metric_type"] != metric_type:
                    raise ValueError("metric type cannot change for a series")
                aggregate = dict(old)
                aggregate["count"] = int(aggregate["count"]) + 1
                if metric_type in {"counter", "histogram"}:
                    aggregate["sum"] = float(aggregate["sum"]) + value
                if metric_type == "histogram":
                    aggregate["min"] = min(float(aggregate["min"]), value)
                    aggregate["max"] = max(float(aggregate["max"]), value)
                aggregate["last"] = value
            aggregate.update(
                metric_type=metric_type,
                metric=metric,
                dimensions=dimensions,
                last_timestamp=point.timestamp,
                last_task_id=task_id,
                last_run_id=run_id,
                last_commit_sha=commit_sha,
            )
            state[key] = aggregate
            return True, state

        self.store.atomic_update(self.STATE_KEY, update, default={})
        return point

    def counter(self, metric: str, increment: float = 1.0, **context: Any) -> MetricPoint:
        return self.record(metric, increment, metric_type="counter", **context)

    def gauge(self, metric: str, value: float, **context: Any) -> MetricPoint:
        return self.record(metric, value, metric_type="gauge", **context)

    def observe(self, metric: str, value: float, **context: Any) -> MetricPoint:
        return self.record(metric, value, metric_type="histogram", **context)

    def duration(self, metric: str, *, task_id: str | None = None, run_id: str | None = None,
                 commit_sha: str | None = None, dimensions: Mapping[str, str] | None = None):
        started = self.clock()

        def finish() -> MetricPoint:
            elapsed_ms = max(0.0, (self.clock() - started) * 1000.0)
            return self.observe(
                metric, elapsed_ms, task_id=task_id, run_id=run_id,
                commit_sha=commit_sha, dimensions=dimensions,
            )
        return finish

    @contextmanager
    def measure(self, metric: str, *, task_id: str | None = None, run_id: str | None = None,
                commit_sha: str | None = None, dimensions: Mapping[str, str] | None = None):
        """Measure a block and always emit one duration sample."""
        finish = self.duration(metric, task_id=task_id, run_id=run_id,
                               commit_sha=commit_sha, dimensions=dimensions)
        try:
            yield
        finally:
            finish()

    def record_request(self, *, success: bool, duration_ms: float | None = None,
                       task_id: str | None = None, run_id: str | None = None,
                       commit_sha: str | None = None,
                       dimensions: Mapping[str, str] | None = None) -> None:
        self.counter("requests.total", 1, task_id=task_id, run_id=run_id,
                     commit_sha=commit_sha, dimensions=dimensions)
        if not success:
            self.counter("requests.errors", 1, task_id=task_id, run_id=run_id,
                         commit_sha=commit_sha, dimensions=dimensions)
        if duration_ms is not None:
            self.observe("requests.latency_ms", duration_ms, task_id=task_id,
                         run_id=run_id, commit_sha=commit_sha, dimensions=dimensions)

    def record_operation(self, *, operation: str, success: bool, duration_ms: float | None = None,
                         retries: int = 0, task_id: str | None = None,
                         run_id: str | None = None, commit_sha: str | None = None) -> None:
        if not isinstance(operation, str) or not operation.strip():
            raise ValueError("operation is required")
        if retries < 0:
            raise ValueError("retries cannot be negative")
        dimensions = {"operation": operation.strip()[:128]}
        self.counter("operations.total", 1, dimensions=dimensions,
                     task_id=task_id, run_id=run_id, commit_sha=commit_sha)
        if success:
            self.counter("operations.success", 1, dimensions=dimensions,
                         task_id=task_id, run_id=run_id, commit_sha=commit_sha)
        else:
            self.counter("operations.errors", 1, dimensions=dimensions,
                         task_id=task_id, run_id=run_id, commit_sha=commit_sha)
        if retries:
            self.counter("operations.retries", retries, dimensions=dimensions,
                         task_id=task_id, run_id=run_id, commit_sha=commit_sha)
        if duration_ms is not None:
            self.observe("operations.duration_ms", duration_ms, dimensions=dimensions,
                          task_id=task_id, run_id=run_id, commit_sha=commit_sha)

    def operation(self, operation: str, *, task_id: str | None = None,
                  run_id: str | None = None, commit_sha: str | None = None):
        started = self.clock()
        state = {"success": False, "retries": 0}
        @contextmanager
        def scope():
            try:
                yield state
                state["success"] = True
            finally:
                self.record_operation(
                    operation=operation, success=state["success"],
                    duration_ms=max(0.0, (self.clock() - started) * 1000.0),
                    retries=int(state["retries"]), task_id=task_id,
                    run_id=run_id, commit_sha=commit_sha,
                )
        return scope()

    def summary(self) -> dict[str, Any]:
        points = self.snapshot()
        return {"series": len(points), "metrics": sorted({p["metric"] for p in points}),
                "ready": self.is_ready()}

    def snapshot(self) -> list[dict[str, Any]]:
        state = self.store.get(self.STATE_KEY, {})
        return [dict(v) for _, v in sorted(state.items())]

    def health(
        self,
        *,
        now: float | None = None,
        max_age_seconds: float = 300.0,
        request_metric: str = "requests.total",
        error_metric: str = "requests.errors",
    ) -> dict[str, Any]:
        if max_age_seconds < 0:
            raise ValueError("max_age_seconds cannot be negative")
        now = float(self.clock() if now is None else now)
        points = self.snapshot()
        req = [p for p in points if p["metric"] == request_metric]
        err = [p for p in points if p["metric"] == error_metric]
        if not req:
            return {"status": "UNKNOWN", "reason": "no request telemetry", "evidence": points}
        newest = max(float(p["last_timestamp"]) for p in req)
        if now - newest > max_age_seconds:
            return {"status": "UNKNOWN", "reason": "telemetry is stale", "age_seconds": now - newest, "evidence": points}
        requests = sum(float(p.get("sum", p.get("last", 0))) for p in req)
        errors = sum(float(p.get("sum", p.get("last", 0))) for p in err)
        error_rate = errors / requests if requests > 0 else 0.0
        return {
            "status": "HEALTHY" if error_rate == 0.0 else "DEGRADED",
            "requests": requests,
            "errors": errors,
            "error_rate": error_rate,
            "telemetry_age_seconds": max(0.0, now - newest),
            "evidence": points,
        }

    def is_ready(self) -> bool:
        return bool(self.store.is_ready())
