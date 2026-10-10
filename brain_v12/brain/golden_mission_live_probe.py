"""Generate hash-backed evidence from an actual reachable Electronic Brain runtime.

The probe never executes missions or changes service state. It performs two
read-only GETs and deliberately cannot satisfy restart/recovery launch gates.
"""
from __future__ import annotations
import hashlib
import ipaddress
import json
import os
import socket
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _safe_base_url(raw: str) -> str:
    parsed = urllib.parse.urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("BRAIN_URL must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("BRAIN_URL must not contain credentials, query, or fragment")
    if parsed.scheme == "http":
        host = parsed.hostname.lower()
        allowed = host in {"localhost"} or host.endswith(".localhost")
        try:
            ip = ipaddress.ip_address(host)
            allowed = ip.is_loopback or ip.is_private
        except ValueError:
            pass
        if not allowed:
            raise ValueError("Plain HTTP is allowed only for localhost or private IP addresses")
    return raw.rstrip("/")


def _get_json(url: str, control_key: str, timeout: float) -> tuple[int, dict[str, Any], str]:
    headers = {"Accept": "application/json"}
    if control_key:
        headers["X-Brain-Control-Key"] = control_key
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status_code = int(response.status)
            raw = response.read(1_000_001)
    except urllib.error.HTTPError as exc:
        raw = exc.read(1_000_001)
        status_code = int(exc.code)
    if len(raw) > 1_000_000:
        raise ValueError("Runtime response exceeded 1 MB safety limit")
    digest = hashlib.sha256(raw).hexdigest()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    return status_code, payload, digest


def probe_runtime(base_url: str, control_key: str = "", timeout: float = 5.0) -> dict[str, Any]:
    base = _safe_base_url(base_url)
    checks: list[dict[str, Any]] = []
    try:
        code, payload, digest = _get_json(base + "/api/system/readiness", control_key, timeout)
        passed = code == 200 and payload.get("ok") is True and str(payload.get("status", "")).upper() == "READY"
        checks.append({"name": "runtime_api_readiness", "passed": passed, "http_status": code, "response_sha256": digest})
    except Exception as exc:
        checks.append({"name": "runtime_api_readiness", "passed": False, "error_type": type(exc).__name__})
    try:
        code, payload, digest = _get_json(base + "/api/golden-missions/worker-status", control_key, timeout)
        worker = payload.get("worker", {})
        passed = (
            code == 200
            and payload.get("ok") is True
            and isinstance(worker, dict)
            and worker.get("mode") == "REMINDERS_ONLY"
            and isinstance(payload.get("enabled"), bool)
        )
        checks.append({"name": "runtime_worker_status", "passed": passed, "http_status": code, "response_sha256": digest})
    except Exception as exc:
        checks.append({"name": "runtime_worker_status", "passed": False, "error_type": type(exc).__name__})
    # Deliberately fail-closed for full closure: these need dedicated real drills.
    checks.extend([
        {"name": "mission_persistence_restart", "passed": False, "reason": "Requires a separately executed real service restart and mission state comparison"},
        {"name": "restore_drill", "passed": False, "reason": "Requires a separately executed checkpoint restore and hash comparison"},
    ])
    passed = all(item.get("passed") is True for item in checks)
    host = urllib.parse.urlparse(base).hostname or "unknown"
    return {
        "schema_version": 1,
        "status": "VERIFIED" if passed else "BLOCKED",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "source": "live_read_only_runtime_probe",
        "target_host": host,
        "checks": checks,
        "safety": {"executes_missions": False, "changes_service_state": False, "stores_control_key": False},
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.getenv("BRAIN_URL", "http://127.0.0.1:8012"))
    parser.add_argument("--output", default=".brain/state/production_runtime_evidence.json")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    if not 0.1 <= args.timeout <= 30:
        parser.error("--timeout must be between 0.1 and 30 seconds")
    result = probe_runtime(args.url, os.getenv("CONTROL_KEY", ""), args.timeout)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "VERIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
