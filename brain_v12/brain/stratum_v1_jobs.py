"""Validated Stratum V1 job and share lifecycle primitives.

No networking, mining loop, pool access, credential loading, or persistence is
performed here. These helpers validate server messages and build coinbase /
merkle data only; they deliberately do not assemble a live-pool header or
claim a share is valid/accepted.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any


def _hex_bytes(value: Any, field: str, *, exact_bytes: int | None = None, max_bytes: int = 1_000_000) -> bytes:
    if not isinstance(value, str) or len(value) % 2 or len(value) > max_bytes * 2:
        raise ValueError("INVALID_HEX_" + field.upper())
    try:
        result = bytes.fromhex(value)
    except ValueError as exc:
        raise ValueError("INVALID_HEX_" + field.upper()) from exc
    if exact_bytes is not None and len(result) != exact_bytes:
        raise ValueError("INVALID_LENGTH_" + field.upper())
    return result


def sha256d(data: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


@dataclass(frozen=True)
class StratumJob:
    job_id: str
    prevhash_hex: str
    coinbase1_hex: str
    coinbase2_hex: str
    merkle_branch_hex: tuple[str, ...]
    version_hex: str
    nbits_hex: str
    ntime_hex: str
    clean_jobs: bool

    @classmethod
    def from_notify(cls, params: Any) -> "StratumJob":
        if not isinstance(params, list) or len(params) != 9:
            raise ValueError("STRATUM_NOTIFY_REQUIRES_9_PARAMS")
        job_id, prevhash, coinbase1, coinbase2, branches, version, nbits, ntime, clean = params
        if not isinstance(job_id, str) or not job_id or len(job_id) > 256:
            raise ValueError("INVALID_JOB_ID")
        _hex_bytes(prevhash, "prevhash", exact_bytes=32)
        _hex_bytes(coinbase1, "coinbase1")
        _hex_bytes(coinbase2, "coinbase2")
        _hex_bytes(version, "version", exact_bytes=4)
        _hex_bytes(nbits, "nbits", exact_bytes=4)
        _hex_bytes(ntime, "ntime", exact_bytes=4)
        if not isinstance(branches, list) or len(branches) > 64:
            raise ValueError("INVALID_MERKLE_BRANCHES")
        for branch in branches:
            _hex_bytes(branch, "merkle_branch", exact_bytes=32)
        if not isinstance(clean, bool):
            raise ValueError("INVALID_CLEAN_JOBS")
        return cls(job_id, prevhash.lower(), coinbase1.lower(), coinbase2.lower(),
                   tuple(x.lower() for x in branches), version.lower(), nbits.lower(),
                   ntime.lower(), clean)


def build_coinbase(job: StratumJob, extranonce1_hex: str, extranonce2_hex: str,
                   extranonce2_size: int) -> bytes:
    if isinstance(extranonce2_size, bool) or not isinstance(extranonce2_size, int) or not 1 <= extranonce2_size <= 32:
        raise ValueError("INVALID_EXTRANONCE2_SIZE")
    ex1 = _hex_bytes(extranonce1_hex, "extranonce1", max_bytes=64)
    ex2 = _hex_bytes(extranonce2_hex, "extranonce2", exact_bytes=extranonce2_size, max_bytes=32)
    return (_hex_bytes(job.coinbase1_hex, "coinbase1") + ex1 + ex2
            + _hex_bytes(job.coinbase2_hex, "coinbase2"))


def merkle_root_from_coinbase(coinbase: bytes, branches_hex: tuple[str, ...]) -> bytes:
    """Return raw SHA256d merkle accumulator bytes; no display-endian conversion."""
    if not isinstance(coinbase, bytes) or not coinbase:
        raise ValueError("INVALID_COINBASE")
    current = sha256d(coinbase)
    for branch_hex in branches_hex:
        branch = _hex_bytes(branch_hex, "merkle_branch", exact_bytes=32)
        current = sha256d(current + branch)
    return current


class ShareLifecycle:
    """In-memory correlation state; a response alone is not durable evidence."""
    def __init__(self) -> None:
        self._pending: dict[int, dict[str, Any]] = {}
        self._next_id = 1

    def register_candidate(self, job_id: str, candidate_fingerprint: str) -> int:
        if not isinstance(job_id, str) or not job_id or not isinstance(candidate_fingerprint, str) or not candidate_fingerprint:
            raise ValueError("INVALID_SHARE_CANDIDATE")
        if len(self._pending) >= 10_000:
            raise ValueError("PENDING_SHARE_LIMIT_REACHED")
        request_id = self._next_id
        self._next_id += 1
        self._pending[request_id] = {"job_id": job_id, "fingerprint": candidate_fingerprint}
        return request_id

    def resolve(self, request_id: int, response: Any) -> dict[str, Any]:
        if isinstance(request_id, bool) or not isinstance(request_id, int) or request_id < 1:
            return {"status": "INVALID_RESPONSE_ID", "pool_acceptance_verified": False}
        pending = self._pending.get(request_id)
        if pending is None:
            return {"status": "UNKNOWN_OR_DUPLICATE_RESPONSE", "pool_acceptance_verified": False}
        # Do not let a malformed or mismatched response consume the real pending
        # request; otherwise a forged response could erase share correlation.
        if not isinstance(response, dict) or response.get("id") != request_id:
            return {"status": "MALFORMED_OR_MISMATCHED_RESPONSE", "pool_acceptance_verified": False}
        self._pending.pop(request_id, None)
        if response.get("error") not in (None, False):
            return {"status": "SHARE_REJECTED_OR_ERROR", "pool_acceptance_verified": False,
                    "job_id": pending["job_id"]}
        if response.get("result") is True:
            return {"status": "POOL_RESPONSE_SAYS_ACCEPTED", "pool_acceptance_verified": False,
                    "job_id": pending["job_id"], "fingerprint": pending["fingerprint"],
                    "evidence_required": ["authenticated_transport", "timestamped_redacted_pool_response",
                                          "independent_pool_dashboard_or_api_confirmation"]}
        return {"status": "INCOMPLETE_OR_REJECTED_RESPONSE", "pool_acceptance_verified": False,
                "job_id": pending["job_id"]}
