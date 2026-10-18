"""Fail-closed Bitcoin Stratum V1 connection probe.

This module verifies TCP/TLS, subscribe, and authorize responses only. It does
not compute or submit shares, prove pool acceptance, or verify revenue.
Network access occurs only when probe_stratum_v1() is explicitly enabled by
an authorized external caller; never invoke it from CI.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import socket
import ssl
import time
from typing import Any


class StratumProtocolError(ValueError):
    """Malformed or unsuccessful Stratum protocol response."""


def encode_request(request_id: int, method: str, params: list[Any]) -> bytes:
    if isinstance(request_id, bool) or not isinstance(request_id, int) or request_id < 1:
        raise ValueError("INVALID_REQUEST_ID")
    if method not in {"mining.subscribe", "mining.authorize"}:
        raise ValueError("UNSUPPORTED_STRATUM_METHOD")
    if not isinstance(params, list):
        raise ValueError("INVALID_PARAMS")
    return (json.dumps({"id": request_id, "method": method, "params": params},
                       separators=(",", ":")) + "\n").encode("utf-8")


def parse_response(line: bytes, expected_id: int) -> dict[str, Any]:
    try:
        message = json.loads(line.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StratumProtocolError("INVALID_JSON_RESPONSE") from exc
    if not isinstance(message, dict) or isinstance(message.get("id"), bool) or message.get("id") != expected_id:
        raise StratumProtocolError("UNEXPECTED_RESPONSE_ID")
    if message.get("error") not in (None, False):
        # Do not echo server error details: pools may include sensitive context.
        raise StratumProtocolError("STRATUM_REQUEST_REJECTED")
    if "result" not in message:
        raise StratumProtocolError("MISSING_RESULT")
    return message


def _read_response(stream: Any, expected_id: int, deadline: float) -> dict[str, Any]:
    while time.monotonic() < deadline:
        line = stream.readline()
        if not line:
            raise StratumProtocolError("POOL_CLOSED_CONNECTION")
        try:
            message = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StratumProtocolError("INVALID_JSON_RESPONSE") from exc
        if isinstance(message, dict) and message.get("id") is None and isinstance(message.get("method"), str):
            # Valid asynchronous notifications are not subscribe/authorize evidence.
            continue
        return parse_response(line, expected_id)
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
    """Probe a caller-authorized endpoint without mining or submitting shares.

    Credentials must be supplied by the caller from a protected environment.
    They are never included in the returned record or exception text.
    """
    if enabled is not True:
        raise RuntimeError("LIVE_POOL_PROBE_DISABLED")
    if not isinstance(host, str) or not host.strip() or any(c in host for c in "\r\n"):
        raise ValueError("INVALID_POOL_HOST")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("INVALID_POOL_PORT")
    if not isinstance(worker_name, str) or not worker_name.strip() or any(c in worker_name for c in "\r\n"):
        raise ValueError("INVALID_WORKER_NAME")
    if not isinstance(worker_password, str) or not worker_password or any(c in worker_password for c in "\r\n"):
        raise ValueError("INVALID_WORKER_PASSWORD")
    try:
        timeout = float(timeout_seconds)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("TIMEOUT_OUT_OF_RANGE") from exc
    if not 0.5 <= timeout <= 30:
        raise ValueError("TIMEOUT_OUT_OF_RANGE")

    started = time.monotonic()
    context = ssl.create_default_context() if use_tls else None
    with socket.create_connection((host.strip(), port), timeout=timeout) as raw:
        raw.settimeout(timeout)
        connection = context.wrap_socket(raw, server_hostname=host.strip()) if context else raw
        with connection, connection.makefile("rwb") as stream:
            stream.write(encode_request(1, "mining.subscribe", ["ElectronicBrainV12/1.0"]))
            stream.flush()
            subscribed = _read_response(stream, 1, time.monotonic() + timeout)
            result = subscribed["result"]
            if not isinstance(result, list) or len(result) < 3 or not isinstance(result[0], list):
                raise StratumProtocolError("MALFORMED_SUBSCRIBE_RESPONSE")
            extranonce1, extranonce2_size = result[1], result[2]
            if (not isinstance(extranonce1, str) or len(extranonce1) % 2
                    or len(extranonce1) > 128
                    or any(ch not in "0123456789abcdefABCDEF" for ch in extranonce1)):
                raise StratumProtocolError("MALFORMED_SUBSCRIBE_EXTRANONCE1")
            if (isinstance(extranonce2_size, bool) or not isinstance(extranonce2_size, int)
                    or not 1 <= extranonce2_size <= 32):
                raise StratumProtocolError("MALFORMED_SUBSCRIBE_EXTRANONCE2_SIZE")

            stream.write(encode_request(2, "mining.authorize", [worker_name, worker_password]))
            stream.flush()
            authorized = _read_response(stream, 2, time.monotonic() + timeout)
            if authorized["result"] is not True:
                raise StratumProtocolError("WORKER_AUTHORIZATION_FAILED")

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
        "pool_contacted": True,
        "share_submitted": False,
        "evidence_class": "STRATUM_CONNECTION_AND_AUTHORIZATION_ONLY",
    }
