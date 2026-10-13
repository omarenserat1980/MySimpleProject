"""Start the software-only cloud worker inside the existing Python service."""
from __future__ import annotations

import os
import threading
import time

from . import cloud_worker_agent

_lock = threading.Lock()
_thread: threading.Thread | None = None
_stop = threading.Event()


def _run() -> None:
    origin = os.getenv("BRAIN_ORIGIN", "https://brain-control-plane-main.onrender.com").strip().rstrip("/")
    timeout = max(2.0, float(os.getenv("BRAIN_CLOUD_WORKER_HTTP_TIMEOUT_SECONDS", "8")))
    import httpx

    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
        while not _stop.is_set():
            try:
                result = cloud_worker_agent.tick(client, origin)
                print({"cloud_worker": result}, flush=True)
            except Exception as exc:
                try:
                    cloud_worker_agent.HEARTBEAT.unlink()
                except FileNotFoundError:
                    pass
                print({"cloud_worker": "TICK_FAILED", "detail": str(exc)[:200]}, flush=True)
            _stop.wait(cloud_worker_agent.INTERVAL)


def start_worker() -> None:
    """Idempotently start a daemon thread; no extra service/process is required."""
    global _thread
    with _lock:
        if _thread is not None and _thread.is_alive():
            return
        _stop.clear()
        _thread = threading.Thread(target=_run, name="brain-cloud-software-worker", daemon=True)
        _thread.start()


def stop_worker() -> None:
    """Request a graceful stop for test/shutdown callers."""
    _stop.set()
