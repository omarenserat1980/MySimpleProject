"""Fail-closed evidence classification for correlated Stratum share responses.

This helper consumes a protocol response line for an existing session. It does
not establish that the line came from a live socket, independently validate
proof-of-work, or establish revenue.
"""
from __future__ import annotations

from typing import Any

from .stratum_v1_protocol import (
    StratumProtocolError,
    StratumV1Session,
    parse_message,
)


def observe_share_response(
    session: StratumV1Session,
    line: str | bytes,
) -> dict[str, Any]:
    """Classify a correlated pool response without overstating its evidence.

    Only a response correlated to a pending share request is accepted.
    A positive response means the pool reported acceptance; it is not proof
    of live transport, independent share validity, payout, or realized revenue.
    """
    if not isinstance(session, StratumV1Session):
        raise StratumProtocolError("STRATUM_V1_SESSION_REQUIRED")

    message = parse_message(line)
    request_id = message.get("id")
    if isinstance(request_id, bool) or not isinstance(request_id, int):
        raise StratumProtocolError("INVALID_RESPONSE_ID")
    if session.pending.get(request_id) != "share":
        raise StratumProtocolError("UNMATCHED_SHARE_RESPONSE")

    outcome = session.receive(line)
    if outcome.get("event") != "SHARE_RESPONSE":
        raise StratumProtocolError("NOT_A_SHARE_RESPONSE")

    status = outcome.get("status")
    if status not in ("ACCEPTED_BY_POOL", "REJECTED_BY_POOL"):
        raise StratumProtocolError("MALFORMED_SHARE_RESPONSE")

    return {
        "evidence_class": "SESSION_CORRELATED_STRATUM_SHARE_RESPONSE",
        "request_id": request_id,
        "pool_reported_status": status,
        "pool_reported_acceptance": status == "ACCEPTED_BY_POOL",
        "live_transport_verified": False,
        "independent_share_validation_verified": False,
        "payout_verified": False,
        "revenue_verified": False,
        "financial_execution_enabled": False,
    }
