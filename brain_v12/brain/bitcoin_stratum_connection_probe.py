"""Fail-closed Bitcoin Stratum V1 connection probe.

This module verifies only TCP/TLS, subscribe, and authorize responses. It does
not compute SHA-256d shares, submit shares, prove accepted shares, or verify
revenue. Network access occurs only when explicitly enabled by an authorized
caller; never call this probe from CI.
"""
from __future__ import annotations

import json
import socket
import ssl
import time
from datetime import datetime, timezone
from typing import Any


class StratumConnectionProbeError(ValueError):
    """Malformed or unsuccessful Stratum protocol response."""


def encode_probe_request(request_id: int, method: str, params: list[Any]) -> bytes:
    if isinstance(request_id, bool) or not isinstance(request_id, int) or request_id < 1:
        raise ValueError("INVALID_REQUEST_ID")
    if method not in {"mining.subscribe", "mining.authorize"}:
        raise ValueError("UNSUPPORTED_STRATUM_METHOD")
    if not isinstance(params, list):
        raise ValueError("INVALID_PARAMS")
    return (json.dumps({"id": request_id, "method": method, "params": params},
                       separators=(",", ":")) + "\n").encode("utf-8")


def _parse_response(line: bytes, expected_id: int) -> dict[str, Any]:
    try:
        message = json.loads(line.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StratumConnectionProbeError("INVALID_JSON_RESPONSE") from exc
    if not isinstance(message, dict) or message.get("id") != expected_id:
        raise StratumConnectionProbeError("UNEXPECTED_RESPONSE_ID")
    if message.get("error") not in (None, False):
        # Never echo server details: they may contain sensitive information.
        raise StratumConnectionProbeError("STRATUM_REQUEST_REJECTED")
    if "result" not in message:
        raise StratumConnectionProbeError("MISSING_RESULT")
    return message


def _read_response(stream, expected_id: int, timeout_seconds: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        line = stream.readline()
        if not line:
            raise StratumConnectionProbeError("POOL_CLOSED_CONNECTION")
        try:
            message = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StratumConnectionProbeError("INVALID_JSON_RESPONSE") from exc
        if isinstance(message, dict) and message.get("id") is None:
            # Notifications are not subscribe/authorization responses.
            continue
        return _parse_response(line, expected_id)
    raise TimeoutError("STRATUM_RESPONSE_TIMEOUT")


def probe_stratum_v1(
    *,
    host: str,
    port: int,
    worker_name: str,
    worker_password: str,
    timeout_seconds: float = 5.0,
    use_tls: bool = True,
    enabled: bool = False,
) -> dict[str, Any]:
    """Probe an explicitly authorized pool endpoint without mining/submitting.

    Credentials must come from a protected caller-side source and are never
    included in the returned evidence or exception text.
    """
    if enabled is not True:
        raise RuntimeError("LIVE_POOL_PROBE_DISABLED")
    if not isinstance(host, str) or not host.strip() or any(c in host for c in "\r\n"):
        raise ValueError("INVALID_POOL_HOST")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("INVALID_POOL_PORT")
    if not isinstance(worker_name, str) or not worker_name.strip() or any(
        c in worker_name for c in "\r\n"
    ):
        raise ValueError("INVALID_WORKER_NAME")
    if not isinstance(worker_password, str) or not worker_password or any(
        c in worker_password for c in "\r\n"
    ):
        raise ValueError("INVALID_WORKER_PASSWORD")
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
        raise ValueError("INVALID_TIMEOUT")
    if not 0.5 <= float(timeout_seconds) <= 30:
        raise ValueError("TIMEOUT_OUT_OF_RANGE")

    started = time.monotonic()
    context = ssl.create_default_context() if use_tls else None
    with socket.create_connection((host.strip(), port), timeout=float(timeout_seconds)) as raw:
        raw.settimeout(float(timeout_seconds))
        connection = context.wrap_socket(raw, server_hostname=host.strip()) if context else raw
        with connection:
            with connection.makefile("rwb") as stream:
                stream.write(encode_probe_request(1, "mining.subscribe", ["ElectronicBrainV12/1.0"]))
                stream.flush()
                subscribed = _read_response(stream, 1, float(timeout_seconds))
                if not subscribed["result"]:
                    raise StratumConnectionProbeError("SUBSCRIBE_REJECTED")
                stream.write(encode_probe_request(2, "mining.authorize", [worker_name, worker_password]))
                stream.flush()
                authorized = _read_response(stream, 2, float(timeout_seconds))
                if authorized["result"] is not True:
                    raise StratumConnectionProbeError("WORKER_AUTHORIZATION_FAILED")

    return {
        "schema_version": "1.0",
        "mode": "connection_probe_only",
        "pool_host": host.strip(),
        "pool_port": port,
        "protocol": "stratum-v1",
        "tls": bool(use_tls),
        "subscribed": True,
        "authorized": True,
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "probe_duration_seconds": round(time.monotonic() - started, 3),
        "live_mining_verified": False,
        "accepted_shares_verified": False,
        "revenue_verified": False,
    }
