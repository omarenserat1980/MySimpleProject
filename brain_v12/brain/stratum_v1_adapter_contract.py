"""Fail-closed Stratum V1 protocol contract for Electronic Brain.

This module validates protocol messages and tracks request/share lifecycle. It is
not a socket transport and never connects to a pool. Live transport must be a
separate reviewed implementation behind an explicit execution gate.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Any

_HEX = re.compile(r"^[0-9a-fA-F]*$")


def _hex_field(value: Any, field: str, *, exact_bytes: int | None = None) -> str:
    if not isinstance(value, str) or not value or len(value) % 2 or not _HEX.fullmatch(value):
        raise ValueError(f"INVALID_{field.upper()}_HEX")
    if exact_bytes is not None and len(value) != exact_bytes * 2:
        raise ValueError(f"INVALID_{field.upper()}_LENGTH")
    return value.lower()


def validate_endpoint(host: str, port: int, *, tls: bool) -> dict[str, Any]:
    """Validate endpoint syntax only; this performs no DNS or network access."""
    if not isinstance(host, str) or not host.strip() or len(host) > 253:
        raise ValueError("INVALID_STRATUM_HOST")
    host = host.strip()
    if any(ord(c) < 33 or ord(c) > 126 for c in host) or any(c in host for c in "/\\@?#"):
        raise ValueError("INVALID_STRATUM_HOST")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("INVALID_STRATUM_PORT")
    if tls is not True:
        raise ValueError("STRATUM_TLS_REQUIRED")
    return {"host": host, "port": port, "tls_required": True, "network_access_performed": False}


@dataclass(frozen=True)
class ShareRecord:
    request_id: int
    job_id: str
    status: str


class StratumV1AdapterContract:
    """Pure protocol state machine; never performs transport or secret logging."""

    transport_mode = "CONTRACT_ONLY_NO_NETWORK"
    live_transport_enabled = False

    def __init__(self, worker_name: str) -> None:
        if not isinstance(worker_name, str) or not worker_name.strip() or len(worker_name) > 128:
            raise ValueError("INVALID_WORKER_NAME")
        if any(ord(c) < 32 for c in worker_name):
            raise ValueError("INVALID_WORKER_NAME")
        self.worker_name = worker_name.strip()
        self._next_id = 1
        self._pending: dict[int, str] = {}
        self._jobs: dict[str, dict[str, Any]] = {}
        self._share_by_request: dict[int, str] = {}
        self._shares: dict[str, ShareRecord] = {}
        self.subscribed = False
        self.authorized = False
        self.difficulty: float | None = None

    def request(self, method: str, params: list[Any]) -> dict[str, Any]:
        if method not in {"mining.subscribe", "mining.authorize"}:
            raise ValueError("UNSUPPORTED_OUTBOUND_METHOD")
        if not isinstance(params, list):
            raise ValueError("INVALID_PARAMS")
        if method == "mining.authorize":
            if len(params) != 2 or params[0] != self.worker_name or not isinstance(params[1], str) or not params[1]:
                raise ValueError("INVALID_AUTHORIZE_PARAMS")
        if method == "mining.subscribe" and params:
            raise ValueError("INVALID_SUBSCRIBE_PARAMS")
        request_id = self._allocate_id()
        self._pending[request_id] = method
        return {"id": request_id, "method": method, "params": params}

    def _allocate_id(self) -> int:
        request_id = self._next_id
        self._next_id += 1
        return request_id

    def handle_notification(self, message: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(message, dict) or message.get("id") is not None:
            raise ValueError("INVALID_NOTIFICATION")
        method, params = message.get("method"), message.get("params")
        if not isinstance(params, list):
            raise ValueError("INVALID_NOTIFICATION_PARAMS")
        if method == "mining.set_difficulty":
            if len(params) != 1 or isinstance(params[0], bool):
                raise ValueError("INVALID_DIFFICULTY")
            try:
                difficulty = float(params[0])
            except (TypeError, ValueError) as exc:
                raise ValueError("INVALID_DIFFICULTY") from exc
            if not math.isfinite(difficulty) or difficulty <= 0:
                raise ValueError("INVALID_DIFFICULTY")
            self.difficulty = difficulty
            return {"status": "DIFFICULTY_UPDATED", "difficulty": difficulty}
        if method == "mining.notify":
            if len(params) < 9 or not isinstance(params[0], str) or not params[0]:
                raise ValueError("INVALID_MINING_NOTIFY")
            job_id = params[0]
            if not isinstance(params[8], bool):
                raise ValueError("INVALID_CLEAN_JOBS_FLAG")
            # Keep only the fields needed for lifecycle checks; no credentials.
            self._jobs[job_id] = {"clean_jobs": params[8]}
            if params[8]:
                self._jobs = {job_id: self._jobs[job_id]}
                self._shares = {
                    share_id: record for share_id, record in self._shares.items()
                    if record.job_id == job_id or record.status in {"ACCEPTED", "REJECTED"}
                }
            return {"status": "JOB_RECEIVED_UNVERIFIED", "job_id": job_id, "clean_jobs": params[8],
                    "pool_acceptance_verified": False}
        raise ValueError("UNSUPPORTED_NOTIFICATION")

    def prepare_share(self, job_id: str, extranonce2_hex: str, ntime_hex: str, nonce_hex: str) -> dict[str, Any]:
        if not self.authorized:
            raise ValueError("STRATUM_SESSION_NOT_AUTHORIZED")
        if job_id not in self._jobs:
            raise ValueError("UNKNOWN_OR_STALE_JOB")
        extranonce2 = _hex_field(extranonce2_hex, "extranonce2")
        ntime = _hex_field(ntime_hex, "ntime", exact_bytes=4)
        nonce = _hex_field(nonce_hex, "nonce", exact_bytes=4)
        request_id = self._allocate_id()
        share_id = f"share-{request_id}"
        self._pending[request_id] = "mining.submit"
        self._share_by_request[request_id] = share_id
        self._shares[share_id] = ShareRecord(request_id, job_id, "SUBMITTED_PENDING_RESPONSE")
        return {
            "id": request_id,
            "method": "mining.submit",
            "params": [self.worker_name, job_id, extranonce2, ntime, nonce],
            "share_id": share_id,
            "status": "SUBMITTED_PENDING_RESPONSE",
            "pool_acceptance_verified": False,
            "network_access_performed": False,
        }

    def handle_response(self, message: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(message, dict) or isinstance(message.get("id"), bool) or not isinstance(message.get("id"), int):
            raise ValueError("INVALID_STRATUM_RESPONSE")
        request_id = message["id"]
        if request_id not in self._pending:
            raise ValueError("UNMATCHED_STRATUM_RESPONSE")
        if message.get("error") is not None:
            method = self._pending.pop(request_id)
            share_id = self._share_by_request.get(request_id)
            if share_id:
                previous = self._shares[share_id]
                self._shares[share_id] = ShareRecord(previous.request_id, previous.job_id, "REJECTED")
            if method == "mining.authorize":
                self.authorized = False
            return {"status": "REJECTED", "method": method, "share_id": share_id,
                    "pool_acceptance_verified": False}
        result = message.get("result")
        method = self._pending.pop(request_id)
        if method == "mining.subscribe":
            if not isinstance(result, list) or len(result) < 3:
                raise ValueError("INVALID_SUBSCRIBE_RESPONSE")
            self.subscribed = True
            return {"status": "SUBSCRIBED", "pool_acceptance_verified": False}
        if method == "mining.authorize":
            self.authorized = result is True
            return {"status": "AUTHORIZED" if self.authorized else "AUTHORIZATION_DENIED",
                    "pool_acceptance_verified": False}
        if method == "mining.submit":
            share_id = self._share_by_request.pop(request_id, None)
            if share_id is None:
                raise ValueError("SHARE_REQUEST_CORRELATION_MISSING")
            previous = self._shares[share_id]
            status = "ACCEPTED" if result is True else "REJECTED"
            self._shares[share_id] = ShareRecord(previous.request_id, previous.job_id, status)
            return {"status": status, "share_id": share_id,
                    "pool_acceptance_verified": result is True,
                    "evidence_class": "POOL_RESPONSE_CORRELATED_TO_REQUEST" if result is True else "REJECTED"}
        raise ValueError("UNSUPPORTED_PENDING_METHOD")

    def status(self) -> dict[str, Any]:
        counts = {state: 0 for state in ("SUBMITTED_PENDING_RESPONSE", "ACCEPTED", "REJECTED")}
        for record in self._shares.values():
            counts[record.status] = counts.get(record.status, 0) + 1
        return {
            "status": "CONTRACT_ONLY",
            "transport_mode": self.transport_mode,
            "live_transport_enabled": False,
            "network_access_performed": False,
            "subscribed": self.subscribed,
            "authorized": self.authorized,
            "known_job_count": len(self._jobs),
            "share_counts": counts,
            "real_mining_verified": False,
            "payout_verified": False,
            "revenue_verified": False,
        }
