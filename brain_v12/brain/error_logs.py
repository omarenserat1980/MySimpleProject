"""Durable, redacted error logs for Electronic Brain.

Records structured JSONL events outside the source tree, with correlation IDs,
tracebacks, request context, and repair lifecycle fields. Never stores request
bodies or authorization headers.
"""
from __future__ import annotations

import json
import os
import re
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

_SECRET_KEY = re.compile(r"(token|secret|password|api[_-]?key|authorization|cookie|credential|private[_-]?key)", re.I)
_lock = threading.Lock()


def _redact(value: Any, key: str = "") -> Any:
    if _SECRET_KEY.search(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(k): _redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact(v) for v in value[:100]]
    if isinstance(value, str):
        value = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._~+/-]+=*", r"\1[REDACTED]", value)
        value = re.sub(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+", r"\1=[REDACTED]", value)
        return value[:12000]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return repr(value)[:2000]


class BrainErrorLogStore:
    """Append-only JSONL log store with safe, bounded read operations."""

    def __init__(self, path: str | Path | None = None):
        default = Path(os.getenv("BRAIN_ERROR_LOG_PATH") or (Path(os.getenv("BRAIN_RUNTIME_HOME", "~/.brain/runtime")).expanduser() / "logs" / "errors.jsonl"))
        self.path = Path(path or default).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self, *, category: str, message: str, severity: str = "ERROR",
        component: str = "unknown", source: str | None = None,
        trace_id: str | None = None, exception: BaseException | None = None,
        context: dict[str, Any] | None = None, status_code: int | None = None,
    ) -> dict[str, Any]:
        event = {
            "schema": "brain-error-log/v1",
            "event_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": severity.upper(),
            "category": category,
            "component": component,
            "source": source,
            "trace_id": trace_id or str(uuid4()),
            "message": str(message)[:4000],
            "exception_type": type(exception).__name__ if exception else None,
            "traceback": ''.join(traceback.format_exception(type(exception), exception, exception.__traceback__))[-12000:]
                if exception else None,
            "status_code": status_code,
            "context": _redact(context or {}),
            "repair": {"status": "PENDING", "attempts": 0, "notes": []},
        }
        event = _redact(event)
        with _lock:
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
                stream.flush()
        return event

    def list(self, *, limit: int = 100, severity: str | None = None,
             category: str | None = None, component: str | None = None) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 1000))
        if not self.path.exists():
            return []
        found = []
        with _lock:
            with self.path.open("r", encoding="utf-8") as stream:
                for line in stream:
                    try:
                        event = json.loads(line)
                    except (json.JSONDecodeError, TypeError):
                        continue
                    if severity and event.get("severity", "").upper() != severity.upper():
                        continue
                    if category and event.get("category") != category:
                        continue
                    if component and event.get("component") != component:
                        continue
                    found.append(event)
        return found[-limit:][::-1]

    def get(self, event_id: str) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        with _lock:
            with self.path.open("r", encoding="utf-8") as stream:
                for line in stream:
                    try:
                        event = json.loads(line)
                    except (json.JSONDecodeError, TypeError):
                        continue
                    if event.get("event_id") == event_id:
                        return event
        return None


class BrainErrorLoggingMiddleware:
    """ASGI middleware: capture uncaught exceptions and HTTP 5xx responses."""

    def __init__(self, app, store: BrainErrorLogStore):
        self.app = app
        self.store = store

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        headers = {k.decode("latin1").lower(): v.decode("latin1") for k, v in scope.get("headers", [])}
        trace_id = headers.get("x-brain-trace-id") or str(uuid4())
        path = scope.get("path", "")
        method = scope.get("method", "UNKNOWN")
        status = {"code": 200}
        async def traced_send(message):
            if message.get("type") == "http.response.start":
                status["code"] = int(message.get("status", 200))
                response_headers = list(message.get("headers", []))
                response_headers.append((b"x-brain-trace-id", trace_id.encode("ascii", "ignore")))
                message["headers"] = response_headers
                if status["code"] >= 500:
                    self.store.record(
                        category="http_server_error", message=f"HTTP {status['code']} for {method} {path}",
                        component="fastapi", source=path, trace_id=trace_id, status_code=status["code"],
                        context={"method": method, "path": path},
                    )
            await send(message)
        try:
            await self.app(scope, receive, traced_send)
        except Exception as exc:
            self.store.record(
                category="unhandled_exception", message=str(exc) or type(exc).__name__,
                component="fastapi", source=path, trace_id=trace_id, exception=exc,
                context={"method": method, "path": path},
            )
            raise
