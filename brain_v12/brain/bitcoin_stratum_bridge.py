"""Explicitly gated local Bitcoin Stratum connectivity bridge.

This module is a connection/authorization probe only: it does not perform
SHA-256d proof-of-work, submit shares, launch a miner, or handle wallet funds.
Run only on a user-owned, authorized host. Never invoke from GitHub Actions.
"""
from __future__ import annotations

import json
import os
import socket
import ssl
from typing import Any


class StratumBridgeError(RuntimeError):
    pass


def _env(name: str) -> str:
    return os.environ.get(name, "").strip()


def bridge_config_from_env() -> dict[str, Any]:
    return {
        "enabled": _env("BRAIN_ENABLE_LIVE_STRATUM_BRIDGE") == "1",
        "host": _env("BRAIN_STRATUM_HOST"),
        "port": _env("BRAIN_STRATUM_PORT"),
        "username": _env("BRAIN_STRATUM_USERNAME"),
        "password": _env("BRAIN_STRATUM_PASSWORD"),
        "tls": _env("BRAIN_STRATUM_TLS") == "1",
        "worker_owned": _env("BRAIN_MINING_WORKER_OWNED") == "1",
        "authorized": _env("BRAIN_MINING_AUTHORIZED") == "1",
    }


def probe_stratum_connection(*, timeout_seconds: float = 5.0) -> dict[str, Any]:
    """Perform Stratum subscribe/authorize on an explicitly configured worker.

    Returns sanitized metadata only; never returns credentials or raw server
    messages. This is not proof-of-work or evidence of accepted mining shares.
    """
    cfg = bridge_config_from_env()
    if _env("GITHUB_ACTIONS").lower() == "true" or _env("CI").lower() == "true":
        raise StratumBridgeError("LIVE_STRATUM_FORBIDDEN_IN_CI")
    if not cfg["enabled"]:
        raise StratumBridgeError("LIVE_STRATUM_BRIDGE_DISABLED")
    if not cfg["worker_owned"] or not cfg["authorized"]:
        raise StratumBridgeError("EXPLICIT_WORKER_OWNERSHIP_AND_AUTHORIZATION_REQUIRED")
    if not all((cfg["host"], cfg["port"], cfg["username"], cfg["password"])):
        raise StratumBridgeError("STRATUM_ENV_CONFIGURATION_INCOMPLETE")
    # Authorization sends a pool password; refuse plaintext Stratum.
    if not cfg["tls"]:
        raise StratumBridgeError("TLS_REQUIRED_TO_PROTECT_POOL_CREDENTIALS")
    try:
        port = int(cfg["port"])
    except ValueError as exc:
        raise StratumBridgeError("INVALID_STRATUM_PORT") from exc
    if not 1 <= port <= 65535:
        raise StratumBridgeError("INVALID_STRATUM_PORT")
    try:
        timeout = float(timeout_seconds)
    except (TypeError, ValueError) as exc:
        raise StratumBridgeError("TIMEOUT_OUT_OF_RANGE") from exc
    if not 0.1 <= timeout <= 15:
        raise StratumBridgeError("TIMEOUT_OUT_OF_RANGE")

    raw: socket.socket | None = None
    sock: socket.socket | None = None
    reader = None
    writer = None
    try:
        raw = socket.create_connection((cfg["host"], port), timeout=timeout)
        if cfg["tls"]:
            context = ssl.create_default_context()
            sock = context.wrap_socket(raw, server_hostname=cfg["host"])
        else:
            sock = raw
        sock.settimeout(timeout)
        reader = sock.makefile("r", encoding="utf-8", newline="\n")
        writer = sock.makefile("w", encoding="utf-8", newline="\n")

        def exchange(message_id: int, method: str, params: list[Any]) -> dict[str, Any]:
            writer.write(json.dumps({"id": message_id, "method": method, "params": params}, separators=(",", ":")) + "\n")
            writer.flush()
            # Pools may send notifications before replying; consume bounded lines.
            for _ in range(20):
                line = reader.readline()
                if not line:
                    raise StratumBridgeError("STRATUM_CONNECTION_CLOSED")
                try:
                    response = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(response, dict) and response.get("id") == message_id:
                    return response
            raise StratumBridgeError("STRATUM_RESPONSE_NOT_FOUND")

        subscribed = exchange(1, "mining.subscribe", ["ElectronicBrain/0.1"])
        subscribe_result = subscribed.get("result")
        if (
            subscribed.get("error") is not None
            or not isinstance(subscribe_result, list)
            or len(subscribe_result) < 3
            or not isinstance(subscribe_result[1], str)
            or not isinstance(subscribe_result[2], int)
            or subscribe_result[2] < 0
        ):
            raise StratumBridgeError("STRATUM_SUBSCRIBE_REJECTED")
        authorized = exchange(2, "mining.authorize", [cfg["username"], cfg["password"]])
        result = authorized.get("result")
        if authorized.get("error") is not None or result is not True:
            raise StratumBridgeError("STRATUM_AUTHORIZATION_REJECTED")
        return {
            "ok": True,
            "status": "STRATUM_SESSION_AUTHENTICATED",
            "host": cfg["host"],
            "port": port,
            "tls": cfg["tls"],
            "algorithm": "sha256d",
            "worker_id": cfg["username"].split(".", 1)[0],
            "proof_of_work_performed": False,
            "shares_submitted": 0,
            "accepted_shares": 0,
            "payout_verified": False,
            "execution_authorized": False,
            "note": "Authenticated Stratum session only; no mining work or revenue is proven.",
        }
    except (OSError, ssl.SSLError, TimeoutError) as exc:
        raise StratumBridgeError("STRATUM_CONNECTION_FAILED:" + type(exc).__name__) from exc
    finally:
        for stream in (writer, reader):
            if stream is not None:
                try:
                    stream.close()
                except OSError:
                    pass
        # If TLS setup fails, close the original socket as well.
        for connection in (sock, raw if sock is None else None):
            if connection is not None:
                try:
                    connection.close()
                except OSError:
                    pass
