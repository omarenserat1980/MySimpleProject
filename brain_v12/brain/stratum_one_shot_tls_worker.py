"""Explicitly gated, one-attempt Stratum V1 TLS worker.

This driver performs at most one bounded nonce search and submits at most one
candidate. It never runs continuously, never logs credentials, and fails closed
unless the operator explicitly enables this operation outside CI. A pool reply
is connection-level evidence only, not independent payout/revenue proof.
"""
from __future__ import annotations

import json
import os
import socket
import ssl
from typing import Any

from .stratum_difficulty_worker_cycle import run_difficulty_bound_offline_cycle
from .stratum_v1_jobs import StratumJob
from .stratum_v1_protocol import StratumProtocolError, StratumV1Session


class OneShotWorkerError(RuntimeError):
    """Sanitized failure for the bounded one-shot worker."""


def _enabled(name: str) -> bool:
    return os.environ.get(name, "").strip() == "1"


def _require_authority() -> None:
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true" or os.environ.get("CI", "").lower() == "true":
        raise OneShotWorkerError("LIVE_WORKER_FORBIDDEN_IN_CI")
    if not _enabled("BRAIN_ENABLE_LIVE_STRATUM_WORKER"):
        raise OneShotWorkerError("LIVE_WORKER_DISABLED")
    if not _enabled("BRAIN_MINING_WORKER_OWNED") or not _enabled("BRAIN_MINING_AUTHORIZED"):
        raise OneShotWorkerError("WORKER_OWNERSHIP_AND_AUTHORIZATION_REQUIRED")
    if os.environ.get("BRAIN_LIVE_WORKER_CONFIRM", "").strip() != "RUN_ONE_BOUNDED_ATTEMPT":
        raise OneShotWorkerError("ONE_ATTEMPT_CONFIRMATION_REQUIRED")
    if os.environ.get("BRAIN_LIVE_SUBMISSION_CONFIRM", "").strip() != "SUBMIT_ONE_SHARE":
        raise OneShotWorkerError("ONE_SHARE_SUBMISSION_CONFIRMATION_REQUIRED")
    if not _enabled("BRAIN_STRATUM_PREVHASH_DIALECT_CONFIRMED"):
        raise OneShotWorkerError("POOL_PREVHASH_DIALECT_CONFIRMATION_REQUIRED")


def _read_line(reader: Any) -> bytes:
    line = reader.readline(1_000_001)
    if not line:
        raise OneShotWorkerError("STRATUM_CONNECTION_CLOSED")
    if len(line) > 1_000_000 or not line.endswith(b"\n"):
        raise OneShotWorkerError("STRATUM_RESPONSE_LINE_INVALID_OR_TOO_LARGE")
    return line


def _consume_until(
    session: StratumV1Session,
    reader: Any,
    *,
    predicate: Any,
    max_lines: int,
    current_job: StratumJob | None = None,
) -> tuple[dict[str, Any] | None, StratumJob | None]:
    for _ in range(max_lines):
        line = _read_line(reader)
        try:
            message = json.loads(line.decode("utf-8"))
            outcome = session.receive(line)
        except (UnicodeDecodeError, json.JSONDecodeError, StratumProtocolError) as exc:
            raise OneShotWorkerError("STRATUM_PROTOCOL_ERROR") from exc
        if isinstance(message, dict) and message.get("method") == "mining.notify":
            try:
                current_job = StratumJob.from_notify(message.get("params"))
            except (TypeError, ValueError) as exc:
                raise OneShotWorkerError("INVALID_MINING_JOB") from exc
        if predicate(outcome, message):
            return outcome, current_job
    raise OneShotWorkerError("STRATUM_RESPONSE_LIMIT_REACHED")


def run_one_bounded_attempt(
    *,
    host: str,
    port: int,
    worker_name: str,
    worker_password: str,
    max_attempts: int = 4096,
    timeout_seconds: float = 5.0,
) -> dict[str, Any]:
    """Connect over verified TLS, authorize, search once, and submit at most one share."""
    _require_authority()
    if not isinstance(host, str) or not host.strip() or any(c in host for c in "\r\n"):
        raise OneShotWorkerError("INVALID_POOL_HOST")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise OneShotWorkerError("INVALID_POOL_PORT")
    if not isinstance(worker_name, str) or not worker_name.strip() or any(c in worker_name for c in "\r\n"):
        raise OneShotWorkerError("INVALID_WORKER_NAME")
    if not isinstance(worker_password, str) or not worker_password or any(c in worker_password for c in "\r\n"):
        raise OneShotWorkerError("INVALID_WORKER_PASSWORD")
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or not 1 <= max_attempts <= 4096:
        raise OneShotWorkerError("MAX_ATTEMPTS_OUT_OF_RANGE")
    try:
        timeout = float(timeout_seconds)
    except (TypeError, ValueError, OverflowError) as exc:
        raise OneShotWorkerError("TIMEOUT_OUT_OF_RANGE") from exc
    if not 0.5 <= timeout <= 15:
        raise OneShotWorkerError("TIMEOUT_OUT_OF_RANGE")

    session = StratumV1Session(worker_name, worker_password)
    context = ssl.create_default_context()
    job: StratumJob | None = None
    try:
        with socket.create_connection((host.strip(), port), timeout=timeout) as raw:
            raw.settimeout(timeout)
            with context.wrap_socket(raw, server_hostname=host.strip()) as tls:
                if not tls.getpeercert(binary_form=True) or not tls.cipher():
                    raise OneShotWorkerError("TLS_PEER_VALIDATION_FAILED")
                with tls.makefile("rwb") as stream:
                    stream.write(session.request_subscribe())
                    stream.flush()
                    _, job = _consume_until(
                        session, stream,
                        predicate=lambda outcome, message: outcome.get("purpose") == "subscribe",
                        max_lines=100,
                        current_job=job,
                    )
                    stream.write(session.request_authorize())
                    stream.flush()
                    _, job = _consume_until(
                        session, stream,
                        predicate=lambda outcome, message: outcome.get("purpose") == "authorize",
                        max_lines=100,
                        current_job=job,
                    )
                    _, job = _consume_until(
                        session, stream,
                        predicate=lambda outcome, message: (
                            session.difficulty is not None
                            and session.current_job_id is not None
                            and session.extranonce1_hex is not None
                            and session.extranonce2_size is not None
                        ),
                        max_lines=100,
                        current_job=job,
                    )
                    if job is None or job.job_id != session.current_job_id:
                        raise OneShotWorkerError("CURRENT_MINING_JOB_REQUIRED")
                    extranonce2 = "00" * session.extranonce2_size
                    cycle = run_difficulty_bound_offline_cycle(
                        session,
                        job,
                        extranonce2=extranonce2,
                        ntime_hex=job.ntime_hex,
                        nonce_start=0,
                        max_attempts=max_attempts,
                        prevhash_dialect_confirmed=True,
                    )
                    if cycle.get("submit_request") is None:
                        return {
                            "status": "NO_CANDIDATE_IN_BOUNDED_RANGE",
                            "attempts": cycle.get("search", {}).get("attempts", 0),
                            "transport_connected": True,
                            "tls_verified": True,
                            "subscribed": session.subscribed,
                            "authorized": session.authorized,
                            "pool_submission_sent": False,
                            "pool_acceptance_verified": False,
                            "real_mining_verified": False,
                            "revenue_verified": False,
                            "evidence_class": "LIVE_TLS_SESSION_BOUNDED_SEARCH_NO_SHARE",
                        }

                    request = cycle["submit_request"]
                    stream.write((json.dumps(
                        {key: request[key] for key in ("id", "method", "params")},
                        separators=(",", ":"),
                    ) + "\n").encode("utf-8"))
                    stream.flush()
                    outcome, _ = _consume_until(
                        session, stream,
                        predicate=lambda result, message: (
                            result.get("event") == "SHARE_RESPONSE"
                            and request["id"] not in session.pending
                        ),
                        max_lines=100,
                        current_job=job,
                    )
                    accepted = bool(outcome and outcome.get("status") == "ACCEPTED_BY_POOL")
                    return {
                        "status": "POOL_REPORTED_SHARE_ACCEPTED" if accepted else "POOL_REPORTED_SHARE_REJECTED",
                        "attempts": cycle.get("search", {}).get("attempts", 0),
                        "transport_connected": True,
                        "tls_verified": True,
                        "subscribed": session.subscribed,
                        "authorized": session.authorized,
                        "pool_submission_sent": True,
                        "pool_acceptance_response_observed": accepted,
                        "pool_acceptance_independently_verified": False,
                        "real_mining_verified": False,
                        "revenue_verified": False,
                        "evidence_class": "ONE_SHOT_LIVE_POOL_RESPONSE_NOT_INDEPENDENTLY_VERIFIED",
                    }
    except OneShotWorkerError:
        raise
    except (OSError, ssl.SSLError, TimeoutError) as exc:
        raise OneShotWorkerError("STRATUM_TRANSPORT_FAILED:" + type(exc).__name__) from exc
