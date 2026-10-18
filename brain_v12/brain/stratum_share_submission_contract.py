"""Offline Stratum V1 share-submission payload contract.

This module validates and serializes candidate submission requests only. It
never opens sockets, reads credentials, submits shares, or asserts pool
acceptance. A separate explicitly authorized live transport must be implemented
and independently evidenced before this can be called a mining worker.
"""
from __future__ import annotations

import json
import re
from typing import Any

from .stratum_v1_protocol import StratumProtocolError, StratumV1Session


_HEX = re.compile(r"^[0-9a-fA-F]+$")


def _required_text(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip() or any(ch in value for ch in "\r\n"):
        raise ValueError(code)
    return value


def _hex_field(value: Any, code: str, *, length: int | None = None) -> str:
    if not isinstance(value, str) or not _HEX.fullmatch(value):
        raise ValueError(code)
    if len(value) % 2:
        raise ValueError(code)
    if length is not None and len(value) != length:
        raise ValueError(code)
    return value.lower()


def build_share_submission(
    *,
    request_id: int,
    worker_name: str,
    job_id: str,
    extranonce2: str,
    ntime: str,
    nonce: str,
) -> dict[str, Any]:
    """Build a validated mining.submit request without sending it."""
    if isinstance(request_id, bool) or not isinstance(request_id, int) or request_id < 1:
        raise ValueError("INVALID_REQUEST_ID")
    worker = _required_text(worker_name, "INVALID_WORKER_NAME")
    job = _required_text(job_id, "INVALID_JOB_ID")
    extra = _hex_field(extranonce2, "INVALID_EXTRANONCE2")
    timestamp = _hex_field(ntime, "INVALID_NTIME", length=8)
    nonce_hex = _hex_field(nonce, "INVALID_NONCE", length=8)
    return {
        "id": request_id,
        "method": "mining.submit",
        "params": [worker, job, extra, timestamp, nonce_hex],
        "sent": False,
        "pool_acceptance_verified": False,
        "real_mining_verified": False,
        "revenue_verified": False,
        "evidence_class": "OFFLINE_VALIDATED_SHARE_CANDIDATE",
    }


def build_session_share_submission(
    session: StratumV1Session,
    *,
    job_id: str,
    extranonce2: str,
    ntime: str,
    nonce: str,
) -> dict[str, Any]:
    """Build a submit candidate through the existing authorized session gate.

    The protocol state machine validates authorization, current job freshness,
    negotiated extranonce width, and field widths. This call only creates a
    pending request; it does not write to a socket or prove pool acceptance.
    """
    if not isinstance(session, StratumV1Session):
        raise ValueError("STRATUM_V1_SESSION_REQUIRED")
    try:
        payload = session.request_submit(job_id, extranonce2, ntime, nonce)
    except StratumProtocolError as exc:
        raise ValueError(str(exc)) from exc
    try:
        request = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AssertionError("SESSION_EMITTED_INVALID_JSON") from exc
    if request.get("method") != "mining.submit" or not isinstance(request.get("id"), int):
        raise AssertionError("SESSION_EMITTED_INVALID_SUBMISSION")
    return {
        "id": request["id"],
        "method": request["method"],
        "params": request["params"],
        "sent": False,
        "pool_acceptance_verified": False,
        "real_mining_verified": False,
        "revenue_verified": False,
        "evidence_class": "OFFLINE_SESSION_VALIDATED_SHARE_CANDIDATE",
    }


def encode_share_submission(**kwargs: Any) -> bytes:
    """Return newline-delimited JSON for an offline fixture."""
    request = build_share_submission(**kwargs)
    wire_request = {key: request[key] for key in ("id", "method", "params")}
    return (json.dumps(wire_request, separators=(",", ":")) + "\n").encode("utf-8")
