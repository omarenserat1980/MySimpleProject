"""Fail-closed Stratum V1 protocol state machine for Electronic Brain.

This module validates protocol messages and builds JSON-RPC requests. It does
not open sockets, construct complete coinbase/merkle/header work, hash pool jobs,
or claim shares are accepted. A network adapter must supply transport separately.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any

from brain_v12.brain.stratum_v1_jobs import StratumJob


class StratumProtocolError(ValueError):
    """Raised when a Stratum V1 message is malformed or out of sequence."""


def encode_request(request_id: int, method: str, params: list[Any]) -> bytes:
    if isinstance(request_id, bool) or not isinstance(request_id, int) or request_id < 1:
        raise StratumProtocolError("INVALID_REQUEST_ID")
    if not isinstance(method, str) or not method or not isinstance(params, list):
        raise StratumProtocolError("INVALID_JSON_RPC_REQUEST")
    return (json.dumps({"id": request_id, "method": method, "params": params},
                       separators=(",", ":")) + "\n").encode("utf-8")


def parse_message(line: str | bytes) -> dict[str, Any]:
    if isinstance(line, bytes):
        try:
            line = line.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise StratumProtocolError("MESSAGE_NOT_UTF8") from exc
    if not isinstance(line, str) or len(line) > 1_000_000:
        raise StratumProtocolError("MESSAGE_INVALID_OR_TOO_LARGE")
    try:
        message = json.loads(line)
    except (json.JSONDecodeError, TypeError) as exc:
        raise StratumProtocolError("INVALID_JSON") from exc
    if not isinstance(message, dict):
        raise StratumProtocolError("MESSAGE_MUST_BE_OBJECT")
    if "method" in message and (not isinstance(message["method"], str) or
                                not isinstance(message.get("params"), list)):
        raise StratumProtocolError("INVALID_NOTIFICATION")
    return message


@dataclass
class StratumV1Session:
    """Protocol bookkeeping only; credentials are never included in snapshots."""
    username: str
    password: str = field(repr=False)
    next_id: int = 1
    subscribed: bool = False
    authorized: bool = False
    difficulty: float | None = None
    current_job_id: str | None = None
    active_job_ids: set[str] = field(default_factory=set)
    pending: dict[int, str] = field(default_factory=dict)
    accepted_shares: int = 0
    rejected_shares: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.username, str) or not self.username.strip():
            raise StratumProtocolError("POOL_USERNAME_REQUIRED")
        if not isinstance(self.password, str) or not self.password:
            raise StratumProtocolError("POOL_PASSWORD_REQUIRED")
        if self.current_job_id:
            self.active_job_ids.add(self.current_job_id)

    def request_subscribe(self, agent: str = "ElectronicBrain/BitcoinLab") -> bytes:
        return self._request("mining.subscribe", [agent], "subscribe")

    def request_authorize(self) -> bytes:
        if not self.subscribed:
            raise StratumProtocolError("SUBSCRIBE_REQUIRED_BEFORE_AUTHORIZE")
        return self._request("mining.authorize", [self.username, self.password], "authorize")

    def request_submit(self, job_id: str, extranonce2: str, ntime: str,
                       nonce: str) -> bytes:
        if not self.authorized:
            raise StratumProtocolError("POOL_AUTHORIZATION_REQUIRED")
        if (not isinstance(job_id, str) or not job_id or not self.current_job_id
                or job_id not in self.active_job_ids):
            raise StratumProtocolError("UNKNOWN_OR_STALE_JOB")
        if (not isinstance(extranonce2, str) or not 2 <= len(extranonce2) <= 64
                or len(extranonce2) % 2
                or any(ch not in "0123456789abcdefABCDEF" for ch in extranonce2)):
            raise StratumProtocolError("INVALID_EXTRANONCE2_HEX_WIDTH")
        for field_name, value in (("NTIME", ntime), ("NONCE", nonce)):
            if (not isinstance(value, str) or len(value) != 8
                    or any(ch not in "0123456789abcdefABCDEF" for ch in value)):
                raise StratumProtocolError("INVALID_" + field_name + "_HEX_WIDTH")
        return self._request("mining.submit",
                             [self.username, job_id, extranonce2, ntime, nonce],
                             "share")

    def _request(self, method: str, params: list[Any], purpose: str) -> bytes:
        request_id = self.next_id
        self.next_id += 1
        self.pending[request_id] = purpose
        return encode_request(request_id, method, params)

    def receive(self, line: str | bytes) -> dict[str, Any]:
        message = parse_message(line)
        if "method" in message:
            method, params = message["method"], message["params"]
            if method == "mining.set_difficulty":
                if len(params) != 1 or isinstance(params[0], bool):
                    raise StratumProtocolError("INVALID_DIFFICULTY")
                try:
                    difficulty = float(params[0])
                except (TypeError, ValueError) as exc:
                    raise StratumProtocolError("INVALID_DIFFICULTY") from exc
                if not math.isfinite(difficulty) or difficulty <= 0:
                    raise StratumProtocolError("INVALID_DIFFICULTY")
                self.difficulty = difficulty
            elif method == "mining.notify":
                try:
                    job = StratumJob.from_notify(params)
                except (TypeError, ValueError) as exc:
                    raise StratumProtocolError("INVALID_MINING_JOB") from exc
                if job.clean_jobs:
                    self.active_job_ids.clear()
                self.active_job_ids.add(job.job_id)
                self.current_job_id = job.job_id
            elif method == "mining.set_extranonce":
                if len(params) != 2 or not isinstance(params[0], str):
                    raise StratumProtocolError("INVALID_EXTRANONCE")
            elif method == "client.reconnect":
                return {"event": "RECONNECT_REQUESTED", "action_required": True}
            else:
                return {"event": "UNSUPPORTED_NOTIFICATION", "method": method}
            return {"event": method, "job_id": self.current_job_id,
                    "difficulty": self.difficulty}
        request_id = message.get("id")
        if request_id is None:
            raise StratumProtocolError("RESPONSE_ID_MISSING")
        if isinstance(request_id, bool) or not isinstance(request_id, int):
            raise StratumProtocolError("INVALID_RESPONSE_ID")
        purpose = self.pending.get(request_id)
        if purpose is None:
            raise StratumProtocolError("UNMATCHED_RESPONSE_ID")
        # A malformed response must not consume the legitimate pending request.
        # Both JSON-RPC response members are required before it can be correlated.
        if "error" not in message or "result" not in message:
            raise StratumProtocolError("MALFORMED_JSON_RPC_RESPONSE")
        error = message["error"]
        result = message["result"]
        if purpose == "subscribe":
            if error is not None:
                self.pending.pop(request_id, None)
                raise StratumProtocolError("SUBSCRIBE_REJECTED_OR_MALFORMED")
            if not isinstance(result, list) or len(result) < 3:
                raise StratumProtocolError("MALFORMED_SUBSCRIBE_RESPONSE")
            self.pending.pop(request_id, None)
            self.subscribed = True
        elif purpose == "authorize":
            if error is not None or result is False:
                self.pending.pop(request_id, None)
                raise StratumProtocolError("POOL_AUTHORIZATION_REJECTED")
            if result is not True:
                raise StratumProtocolError("MALFORMED_AUTHORIZE_RESPONSE")
            self.pending.pop(request_id, None)
            self.authorized = True
        elif purpose == "share":
            if error is None and result is True:
                self.pending.pop(request_id, None)
                self.accepted_shares += 1
                return {"event": "SHARE_RESPONSE", "status": "ACCEPTED_BY_POOL",
                        "accepted_shares": self.accepted_shares}
            if error is not None or result is False:
                self.pending.pop(request_id, None)
                self.rejected_shares += 1
                return {"event": "SHARE_RESPONSE", "status": "REJECTED_BY_POOL",
                        "accepted_shares": self.accepted_shares,
                        "rejected_shares": self.rejected_shares}
            raise StratumProtocolError("MALFORMED_SHARE_RESPONSE")
        return {"event": "RESPONSE", "purpose": purpose, "success": True}

    def snapshot(self) -> dict[str, Any]:
        return {
            "protocol": "STRATUM_V1",
            "transport_connected": False,
            "subscribed": self.subscribed,
            "authorized": self.authorized,
            "difficulty": self.difficulty,
            "current_job_id": self.current_job_id,
            "active_job_count": len(self.active_job_ids),
            "pending_requests": len(self.pending),
            "accepted_shares_reported_by_pool": self.accepted_shares,
            "rejected_shares_reported_by_pool": self.rejected_shares,
            "header_construction_implemented": False,
            "proof_of_work_validation_implemented": False,
            "real_bitcoin_mining": False,
            "revenue_verified": False,
        }
