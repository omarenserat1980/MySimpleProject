import hashlib
import json
import os
import re
import threading
import time
from datetime import datetime, timezone
from typing import Callable, Optional

import httpx


class RenderLogMonitor:
    """Poll Render logs, detect incidents, and persist high-level incident facts."""

    ERROR_PATTERNS = [
        ("CRITICAL", re.compile(r"\b(502|503|504)\b|traceback|fatal|panic|out of memory|oom", re.I)),
        ("ERROR", re.compile(r"\b(error|exception|failed|failure|timeout|timed out|connection refused|importerror|syntaxerror)\b", re.I)),
        ("WARNING", re.compile(r"\b(warn|warning|degraded|retry)\b", re.I)),
    ]

    def __init__(
        self,
        store,
        incident_callback: Optional[Callable[[dict], None]] = None,
        api_key: Optional[str] = None,
        owner_id: Optional[str] = None,
        service_id: Optional[str] = None,
        poll_seconds: Optional[int] = None,
    ):
        self.store = store
        self.incident_callback = incident_callback
        self.api_key = api_key or os.getenv("RENDER_API_KEY", "")
        self.owner_id = owner_id or os.getenv("RENDER_OWNER_ID", "")
        self.service_id = service_id or os.getenv("RENDER_SERVICE_ID", "")
        self.poll_seconds = int(poll_seconds or os.getenv("RENDER_LOG_POLL_SECONDS", "60"))
        self.base_url = os.getenv("RENDER_API_BASE", "https://api.render.com/v1").rstrip("/")
        self._thread = None
        self._stop = threading.Event()

    @property
    def configured(self):
        return bool(self.api_key and self.owner_id and self.service_id)

    def status(self):
        state = self.store.monitor_state()
        return {
            "enabled": os.getenv("BRAIN_RENDER_MONITOR_ENABLED", "false").lower() == "true",
            "configured": self.configured,
            "service_id": self.service_id or None,
            "poll_seconds": self.poll_seconds,
            "last_poll": state.get("last_poll"),
            "last_error": state.get("last_error"),
            "last_log_time": state.get("last_log_time"),
            "logs_seen": state.get("logs_seen", 0),
            "incidents_seen": state.get("incidents_seen", 0),
            "running": bool(self._thread and self._thread.is_alive()),
        }

    def _headers(self):
        return {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}

    def _params(self, start_time, end_time):
        return {
            "ownerId": self.owner_id,
            "resource": self.service_id,
            "startTime": start_time,
            "endTime": end_time,
            "direction": "forward",
            "limit": 100,
        }

    def _fetch_logs(self, start_time, end_time):
        response = httpx.get(
            f"{self.base_url}/logs",
            headers=self._headers(),
            params=self._params(start_time, end_time),
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

    def _log_text(self, item):
        if isinstance(item, str):
            return item
        if not isinstance(item, dict):
            return str(item)
        for key in ("message", "text", "msg", "log", "description"):
            if item.get(key):
                return str(item[key])
        return json.dumps(item, ensure_ascii=False)

    def _log_time(self, item):
        if isinstance(item, dict):
            for key in ("timestamp", "time", "createdAt", "created_at"):
                if item.get(key):
                    return str(item[key])
        return datetime.now(timezone.utc).isoformat()

    def _severity(self, text):
        for severity, pattern in self.ERROR_PATTERNS:
            if pattern.search(text):
                return severity
        return None

    def _fingerprint(self, text):
        normalized = re.sub(r"\d+", "#", text.lower())
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:20]

    def _incident(self, item):
        text = self._log_text(item)
        severity = self._severity(text)
        if not severity:
            return None
        fingerprint = self._fingerprint(text)
        return {
            "fingerprint": fingerprint,
            "severity": severity,
            "message": text[:4000],
            "timestamp": self._log_time(item),
            "service_id": self.service_id,
            "source": "render_api",
            "status": "OPEN",
        }

    def poll_once(self):
        if not self.configured:
            result = {"ok": False, "status": "NOT_CONFIGURED", "required": ["RENDER_API_KEY", "RENDER_OWNER_ID", "RENDER_SERVICE_ID"]}
            self.store.set_monitor_state({"last_poll": time.time(), "last_error": "Render monitor is not configured"})
            return result

        state = self.store.monitor_state()
        now_ts = time.time()
        start_ts = float(state.get("cursor_time") or (now_ts - max(self.poll_seconds * 2, 120)))
        end_ts = now_ts
        try:
            seen = 0
            incidents = []
            latest_time = state.get("last_log_time")
            page_start, page_end = start_ts, end_ts

            # Render paginates by timestamp. Follow the cursor for a bounded
            # number of pages so a burst of logs cannot create an unbounded poll.
            for _ in range(5):
                data = self._fetch_logs(page_start, page_end)
                items = data.get("logs") or data.get("items") or data.get("data") or []
                for item in items:
                    seen += 1
                    log_time = self._log_time(item)
                    latest_time = log_time
                    incident = self._incident(item)
                    if incident:
                        stored = self.store.upsert_incident(incident)
                        incidents.append(stored)
                        if stored.get("new") and self.incident_callback:
                            try:
                                self.incident_callback(stored)
                            except Exception as callback_error:
                                self.store.event("RENDER_MONITOR_CALLBACK_ERROR", {"error": str(callback_error)})

                if not data.get("hasMore"):
                    break
                next_start = data.get("nextStartTime")
                next_end = data.get("nextEndTime")
                if next_start is None or next_end is None:
                    break
                page_start, page_end = next_start, next_end

            new_state = {
                "last_poll": time.time(),
                "last_error": None,
                "cursor_time": end_ts,
                "last_log_time": latest_time,
                "logs_seen": int(state.get("logs_seen", 0)) + seen,
                "incidents_seen": int(state.get("incidents_seen", 0)) + len(incidents),
            }
            self.store.set_monitor_state(new_state)
            self.store.event("RENDER_LOG_POLL", {"logs": seen, "incidents": len(incidents), "service_id": self.service_id})
            return {"ok": True, "status": "COMPLETED", "logs_seen": seen, "incidents": incidents}
        except Exception as exc:
            self.store.set_monitor_state({
                **state,
                "last_poll": time.time(),
                "last_error": str(exc),
                "cursor_time": end_ts,
            })
            self.store.event("RENDER_LOG_POLL_FAILED", {"error": str(exc), "service_id": self.service_id})
            return {"ok": False, "status": "POLL_FAILED", "error": str(exc)}

    def _loop(self):
        while not self._stop.wait(max(self.poll_seconds, 10)):
            self.poll_once()

    def start(self):
        if self._thread and self._thread.is_alive():
            return {"ok": True, "status": "ALREADY_RUNNING"}
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="render-log-monitor", daemon=True)
        self._thread.start()
        return {"ok": True, "status": "STARTED", "poll_seconds": self.poll_seconds}

    def stop(self):
        self._stop.set()
        return {"ok": True, "status": "STOP_REQUESTED"}
