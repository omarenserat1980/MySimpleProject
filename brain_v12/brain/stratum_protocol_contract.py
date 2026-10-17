"""Strict, side-effect-free Stratum V1 message contracts for Brain.

This module validates protocol payloads only. It opens no sockets, performs no
mining, reads no credentials from the environment, and submits no shares.
Live operation requires a separately reviewed TLS transport and host/resource
authorization gate.
"""
from __future__ import annotations

import json
import math
import re
from typing import Any

MAX_MESSAGE_BYTES = 1_048_576
_HEX = re.compile(r"^[0-9a-fA-F]+$")
_ALLOWED_METHODS = frozenset({"mining.subscribe", "mining.authorize", "mining.submit"})


class StratumProtocolError(ValueError):
    """Raised when an untrusted Stratum message violates the contract."""


def parse_json_line(raw: str | bytes, *, max_bytes: int = MAX_MESSAGE_BYTES) -> dict[str, Any]:
    """Parse exactly one bounded JSON object from a Stratum newline frame."""
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or not 1 <= max_bytes <= MAX_MESSAGE_BYTES:
        raise StratumProtocolError("INVALID_MAX_MESSAGE_BYTES")
    if isinstance(raw, bytes):
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise StratumProtocolError("INVALID_UTF8") from exc
    elif isinstance(raw, str):
        text = raw
    else:
        raise StratumProtocolError("MESSAGE_MUST_BE_TEXT_OR_BYTES")
    if not text or len(text.encode("utf-8")) > max_bytes:
        raise StratumProtocolError("MESSAGE_SIZE_OUT_OF_RANGE")
    text = text.rstrip("\r\n")
    if "\n" in text or "\r" in text:
        raise StratumProtocolError("MULTIPLE_FRAMES_NOT_ALLOWED")
    try:
        value = json.loads(text)
    except (json.JSONDecodeError, ValueError) as exc:
        raise StratumProtocolError("INVALID_JSON") from exc
    if not isinstance(value, dict):
        raise StratumProtocolError("JSON_OBJECT_REQUIRED")
    return value


def build_request(request_id: int, method: str, params: list[Any]) -> dict[str, Any]:
    """Build a JSON-RPC request for a narrow set of Stratum V1 methods."""
    if isinstance(request_id, bool) or not isinstance(request_id, int) or request_id < 1:
        raise StratumProtocolError("INVALID_REQUEST_ID")
    if method not in _ALLOWED_METHODS:
        raise StratumProtocolError("METHOD_NOT_ALLOWED")
    if not isinstance(params, list) or len(params) > 16:
        raise StratumProtocolError("INVALID_PARAMS")
    return {"id": request_id, "method": method, "params": params}


def build_subscribe_request(request_id: int, user_agent: str) -> dict[str, Any]:
    if not isinstance(user_agent, str) or not user_agent.strip() or len(user_agent) > 128:
        raise StratumProtocolError("INVALID_USER_AGENT")
    if any(ord(char) < 32 for char in user_agent):
        raise StratumProtocolError("INVALID_USER_AGENT")
    return build_request(request_id, "mining.subscribe", [user_agent])


def build_authorize_request(request_id: int, username: str, password: str) -> dict[str, Any]:
    """Construct an authorization payload without storing or transmitting it."""
    for name, value, maximum in (("username", username, 256), ("password", password, 512)):
        if not isinstance(value, str) or not value or len(value) > maximum:
            raise StratumProtocolError(f"INVALID_{name.upper()}")
        if any(ord(char) < 32 for char in value):
            raise StratumProtocolError(f"INVALID_{name.upper()}")
    return build_request(request_id, "mining.authorize", [username, password])


def _hex_field(
    value: Any,
    name: str,
    *,
    min_length: int = 1,
    max_length: int = 256,
    allow_empty: bool = False,
) -> str:
    if not isinstance(value, str):
        raise StratumProtocolError(f"INVALID_{name.upper()}")
    if allow_empty and value == "":
        return ""
    if (
        not min_length <= len(value) <= max_length
        or len(value) % 2
        or not _HEX.fullmatch(value)
    ):
        raise StratumProtocolError(f"INVALID_{name.upper()}")
    return value.lower()


def build_submit_request(
    request_id: int,
    username: str,
    job_id: str,
    extranonce2: str,
    ntime: str,
    nonce: str,
) -> dict[str, Any]:
    """Build a pool share submission payload; does not send or claim acceptance."""
    if not isinstance(username, str) or not username or len(username) > 256:
        raise StratumProtocolError("INVALID_USERNAME")
    if not isinstance(job_id, str) or not job_id or len(job_id) > 256:
        raise StratumProtocolError("INVALID_JOB_ID")
    if any(ord(char) < 32 for char in username + job_id):
        raise StratumProtocolError("INVALID_TEXT_FIELD")
    extranonce2 = _hex_field(extranonce2, "extranonce2", max_length=128)
    ntime = _hex_field(ntime, "ntime", min_length=8, max_length=8)
    nonce = _hex_field(nonce, "nonce", min_length=8, max_length=8)
    return build_request(
        request_id,
        "mining.submit",
        [username, job_id, extranonce2, ntime, nonce],
    )


def parse_response(message: dict[str, Any], expected_id: int) -> dict[str, Any]:
    """Validate a JSON-RPC response envelope without treating it as pool proof."""
    if not isinstance(message, dict):
        raise StratumProtocolError("RESPONSE_OBJECT_REQUIRED")
    if isinstance(expected_id, bool) or not isinstance(expected_id, int) or expected_id < 1:
        raise StratumProtocolError("INVALID_EXPECTED_RESPONSE_ID")
    response_id = message.get("id")
    if isinstance(response_id, bool) or response_id != expected_id:
        raise StratumProtocolError("RESPONSE_ID_MISMATCH")
    if "result" not in message or "error" not in message:
        raise StratumProtocolError("RESPONSE_FIELDS_REQUIRED")
    error = message["error"]
    if error is not None and not isinstance(error, (list, dict, str)):
        raise StratumProtocolError("INVALID_RESPONSE_ERROR")
    reports_acceptance = message["result"] is True and error is None
    return {
        "request_id": expected_id,
        "result": message["result"],
        "error": error,
        "pool_response_reports_acceptance": reports_acceptance,
        # Compatibility field: this is only the response's claim, never proof.
        "accepted": reports_acceptance,
        "source": "untrusted_stratum_response_requires_transport_and_session_verification",
    }


def parse_difficulty(params: Any) -> float:
    if not isinstance(params, list) or len(params) != 1:
        raise StratumProtocolError("INVALID_DIFFICULTY_PARAMS")
    value = params[0]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise StratumProtocolError("INVALID_DIFFICULTY")
    difficulty = float(value)
    if not math.isfinite(difficulty) or difficulty <= 0:
        raise StratumProtocolError("INVALID_DIFFICULTY")
    return difficulty


def parse_notify(params: Any) -> dict[str, Any]:
    """Validate fixed-width Stratum job fields before any header construction."""
    if not isinstance(params, list) or len(params) < 9:
        raise StratumProtocolError("INVALID_NOTIFY_PARAMS")
    job_id, prevhash, coinb1, coinb2, branches, version, nbits, ntime, clean = params[:9]
    if (
        not isinstance(job_id, str)
        or not job_id
        or len(job_id) > 256
        or any(ord(char) < 32 for char in job_id)
    ):
        raise StratumProtocolError("INVALID_JOB_ID")
    prevhash = _hex_field(prevhash, "prevhash", min_length=64, max_length=64)
    coinb1 = _hex_field(coinb1, "coinb1", min_length=0, max_length=MAX_MESSAGE_BYTES * 2, allow_empty=True)
    coinb2 = _hex_field(coinb2, "coinb2", min_length=0, max_length=MAX_MESSAGE_BYTES * 2, allow_empty=True)
    version = _hex_field(version, "version", min_length=8, max_length=8)
    nbits = _hex_field(nbits, "nbits", min_length=8, max_length=8)
    ntime = _hex_field(ntime, "ntime", min_length=8, max_length=8)
    if not isinstance(branches, list) or len(branches) > 4096:
        raise StratumProtocolError("INVALID_MERKLE_BRANCHES")
    normalized_branches = [
        _hex_field(item, "merkle_branch", min_length=64, max_length=64)
        for item in branches
    ]
    if not isinstance(clean, bool):
        raise StratumProtocolError("INVALID_CLEAN_JOBS_FLAG")
    return {
        "job_id": job_id,
        "prevhash": prevhash,
        "coinb1": coinb1,
        "coinb2": coinb2,
        "merkle_branches": normalized_branches,
        "version": version,
        "nbits": nbits,
        "ntime": ntime,
        "clean_jobs": clean,
        "share_accepted": False,
        "source": "untrusted_pool_job_notification",
    }
