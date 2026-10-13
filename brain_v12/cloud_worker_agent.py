"""Software-only cloud worker for Electronic Brain.

Run as a supervised sidecar process in the existing Brain service environment.
It writes the heartbeat consumed by /health only after checking the configured
Brain origin and confirming the software-only worker registry is available.
No hardware discovery, credential creation, or external resource provisioning.
"""
from __future__ import annotations

import json
import os
import signal
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx

SERVICE = "brain-cloud-runtime"
WORKER_ID = os.getenv("BRAIN_CLOUD_WORKER_ID", "brain-cloud-software-worker-v1")
INTERVAL = max(5, int(os.getenv("BRAIN_CLOUD_WORKER_INTERVAL_SECONDS", "5")))
LEASE = max(10, int(os.getenv("BRAIN_CLOUD_WORKER_LEASE_SECONDS", "30")))
ROOT = Path(os.getenv("BRAIN_RUNTIME_ROOT", "/var/lib/brain/runtime")).expanduser()
HEARTBEAT = ROOT / "cloud-worker-heartbeat.json"
STOP = False


def _stop(_signum, _frame):
    global STOP
    STOP = True


def _https_origin(value: str) -> bool:
    try:
        parsed = urlparse(value)
        return parsed.scheme == "https" and bool(parsed.netloc) and not parsed.username and not parsed.password
    except ValueError:
        return False


def preflight(client: httpx.Client, origin: str) -> dict:
    if not _https_origin(origin):
        return {"verified": False, "reason": "BRAIN_ORIGIN_HTTPS_REQUIRED"}
    try:
        health_response = client.get(origin + "/health")
        workers_response = client.get(origin + "/api/brain/workers")
        health = health_response.json()
        workers = workers_response.json()
        checks = {
            "health_http_200": health_response.status_code == 200,
            "health_ok": health.get("ok") is True,
            "deployment_converged": health.get("deployment", {}).get("converged") is True,
            "software_only_registry": workers_response.status_code == 200 and workers.get("mode") == "software-only" and workers.get("device_adapters_enabled") is False,
        }
        ok = all(checks.values())
        return {"verified": ok, "checks": checks, "deployment": health.get("deployment", {})}
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        return {"verified": False, "reason": "PREFLIGHT_FAILED", "detail": str(exc)[:200]}


def write_heartbeat(payload: dict) -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".cloud-worker-heartbeat-", suffix=".tmp", dir=str(ROOT))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp_name, HEARTBEAT)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def tick(client: httpx.Client, origin: str) -> dict:
    checked = preflight(client, origin)
    now = time.time()
    if not checked.get("verified"):
        # Do not preserve a stale RUNNING attestation when verification fails.
        try:
            HEARTBEAT.unlink()
        except FileNotFoundError:
            pass
        return {"ok": False, "state": "BLOCKED", "preflight": checked}
    try:
        response = client.post(
            origin + "/api/brain/workers/register",
            json={
                "worker_id": WORKER_ID,
                "kind": "software",
                "capabilities": ["brain-health-check", "software-only-orchestration", "heartbeat"],
                "lease_seconds": LEASE,
            },
        )
        registration = response.json()
        if response.status_code != 200 or registration.get("ok") is not True:
            raise RuntimeError("WORKER_REGISTRATION_REJECTED")
    except (httpx.HTTPError, ValueError, RuntimeError) as exc:
        try:
            HEARTBEAT.unlink()
        except FileNotFoundError:
            pass
        return {"ok": False, "state": "REGISTRATION_FAILED", "detail": str(exc)[:200]}
    payload = {
        "service": SERVICE,
        "state": "RUNNING",
        "timestamp": now,
        "worker_id": WORKER_ID,
        "preflight": {"verified": True, "checks": checked.get("checks", {})},
        "registration": {"verified": True, "mode": registration.get("mode", "software-only")},
    }
    write_heartbeat(payload)
    return {"ok": True, "state": "RUNNING", "worker_id": WORKER_ID, "timestamp": now}


def main() -> int:
    origin = os.getenv("BRAIN_ORIGIN", "").strip().rstrip("/")
    if not _https_origin(origin):
        print(json.dumps({"ok": False, "state": "BLOCKED_CONFIGURATION", "reason": "BRAIN_ORIGIN_HTTPS_REQUIRED"}))
        return 2
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    timeout = max(2.0, float(os.getenv("BRAIN_CLOUD_WORKER_HTTP_TIMEOUT_SECONDS", "8")))
    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
        while not STOP:
            result = tick(client, origin)
            print(json.dumps(result, sort_keys=True), flush=True)
            if not result.get("ok"):
                # Fail closed: retry without leaving a false live heartbeat.
                time.sleep(INTERVAL)
            else:
                time.sleep(INTERVAL)
    try:
        HEARTBEAT.unlink()
    except FileNotFoundError:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
