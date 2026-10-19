"""Fail-closed, one-share Stratum V1 TLS transport adapter.

This adapter sends at most one pre-built mining.submit request on a caller-owned,
certificate-verified TLS socket. It never creates sockets, reads credentials, loops
mining, or treats a pool reply as independent payout/revenue evidence. Live use
requires multiple explicit environment gates and is forbidden in CI.
"""
from __future__ import annotations

import json
import os
import ssl
from typing import Any

from .stratum_v1_protocol import StratumProtocolError, StratumV1Session


class StratumTLSTransportError(RuntimeError):
    """Sanitized failure from the bounded TLS share transport."""


def _enabled(name: str) -> bool:
    return os.environ.get(name, "").strip() == "1"


def _require_live_submit_authority() -> None:
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true" or os.environ.get("CI", "").lower() == "true":
        raise StratumTLSTransportError("LIVE_STRATUM_SUBMIT_FORBIDDEN_IN_CI")
    if not _enabled("BRAIN_ENABLE_LIVE_STRATUM_SUBMIT"):
        raise StratumTLSTransportError("LIVE_STRATUM_SUBMIT_DISABLED")
    if not _enabled("BRAIN_MINING_WORKER_OWNED") or not _enabled("BRAIN_MINING_AUTHORIZED"):
        raise StratumTLSTransportError("EXPLICIT_WORKER_OWNERSHIP_AND_AUTHORIZATION_REQUIRED")
    if os.environ.get("BRAIN_LIVE_SUBMISSION_CONFIRM", "").strip() != "SUBMIT_ONE_SHARE":
        raise StratumTLSTransportError("EXPLICIT_ONE_SHARE_CONFIRMATION_REQUIRED")


def send_one_share(
    session: StratumV1Session,
    tls_socket: ssl.SSLSocket,
    submit_request: dict[str, Any],
    *,
    timeout_seconds: float = 5.0,
    max_response_lines: int = 20,
) -> dict[str, Any]:
    """Send one already-computed share and correlate its pool response.

    The caller owns connection creation, TLS hostname verification, subscription,
    authorization and job reception. This function refuses ordinary sockets and
    requires the session's matching pending share request. A positive reply means
    only that this pool connection returned result=true; it is not payout evidence.
    """
    _require_live_submit_authority()
    if not isinstance(session, StratumV1Session) or not session.authorized:
        raise StratumTLSTransportError("AUTHORIZED_STRATUM_SESSION_REQUIRED")
    if not isinstance(tls_socket, ssl.SSLSocket):
        raise StratumTLSTransportError("VERIFIED_TLS_SOCKET_REQUIRED")
    try:
        certificate = tls_socket.getpeercert(binary_form=True)
        cipher = tls_socket.cipher()
    except (OSError, ssl.SSLError, ValueError) as exc:
        raise StratumTLSTransportError("TLS_PEER_VALIDATION_FAILED") from exc
    if not certificate or not cipher:
        raise StratumTLSTransportError("TLS_PEER_CERTIFICATE_REQUIRED")
    context = tls_socket.context
    if (not isinstance(context, ssl.SSLContext)
            or context.verify_mode != ssl.CERT_REQUIRED
            or context.check_hostname is not True):
        raise StratumTLSTransportError("TLS_CERTIFICATE_AND_HOSTNAME_VERIFICATION_REQUIRED")

    if not isinstance(submit_request, dict):
        raise StratumTLSTransportError("INVALID_SUBMIT_REQUEST")
    request_id = submit_request.get("id")
    if (isinstance(request_id, bool) or not isinstance(request_id, int)
            or submit_request.get("method") != "mining.submit"
            or not isinstance(submit_request.get("params"), list)
            or len(submit_request["params"]) != 5):
        raise StratumTLSTransportError("INVALID_SUBMIT_REQUEST")
    if session.pending.get(request_id) != "share":
        raise StratumTLSTransportError("MATCHING_PENDING_SHARE_REQUIRED")
    params = submit_request["params"]
    if params[0] != session.username or params[1] != session.current_job_id:
        raise StratumTLSTransportError("SUBMIT_WORKER_OR_JOB_MISMATCH")
    if params[1] not in session.active_job_ids:
        raise StratumTLSTransportError("STALE_SHARE_JOB")

    try:
        timeout = float(timeout_seconds)
    except (TypeError, ValueError) as exc:
        raise StratumTLSTransportError("TIMEOUT_OUT_OF_RANGE") from exc
    if not 0.1 <= timeout <= 15:
        raise StratumTLSTransportError("TIMEOUT_OUT_OF_RANGE")
    if (isinstance(max_response_lines, bool) or not isinstance(max_response_lines, int)
            or not 1 <= max_response_lines <= 100):
        raise StratumTLSTransportError("RESPONSE_LINE_LIMIT_OUT_OF_RANGE")

    wire = (json.dumps(
        {key: submit_request[key] for key in ("id", "method", "params")},
        separators=(",", ":"),
    ) + "\n").encode("utf-8")
    reader = None
    try:
        tls_socket.settimeout(timeout)
        reader = tls_socket.makefile("rb")
        tls_socket.sendall(wire)
        for _ in range(max_response_lines):
            line = reader.readline(1_000_001)
            if not line:
                raise StratumTLSTransportError("STRATUM_CONNECTION_CLOSED")
            if len(line) > 1_000_000 or not line.endswith(b"\n"):
                raise StratumTLSTransportError("STRATUM_RESPONSE_LINE_INVALID_OR_TOO_LARGE")
            try:
                outcome = session.receive(line)
            except StratumProtocolError as exc:
                # Do not expose raw pool payloads or credential-bearing messages.
                raise StratumTLSTransportError("STRATUM_RESPONSE_PROTOCOL_ERROR:" + str(exc)) from exc
            if outcome.get("event") == "SHARE_RESPONSE" and request_id not in session.pending:
                accepted = outcome.get("status") == "ACCEPTED_BY_POOL"
                return {
                    "status": "POOL_REPORTED_SHARE_ACCEPTED" if accepted else "POOL_REPORTED_SHARE_REJECTED",
                    "request_id": request_id,
                    "transport_connected": True,
                    "tls_peer_certificate_present": True,
                    "pool_acceptance_response_observed": accepted,
                    "independent_share_validation_verified": False,
                    "payout_verified": False,
                    "revenue_verified": False,
                    "evidence_class": "LIVE_TLS_POOL_RESPONSE_NOT_INDEPENDENTLY_VERIFIED",
                }
        raise StratumTLSTransportError("MATCHING_SHARE_RESPONSE_NOT_FOUND")
    except (OSError, ssl.SSLError, TimeoutError) as exc:
        raise StratumTLSTransportError("STRATUM_TRANSPORT_FAILED:" + type(exc).__name__) from exc
    finally:
        if reader is not None:
            try:
                reader.close()
            except OSError:
                pass
