"""Evidence gate for identifying live software executor nodes.

This proves possession of a configured per-node secret and a fresh response from
software. It does NOT prove physical hardware identity or tamper-resistant hosting.
Secrets must be provisioned out of band and must never be committed to the repo.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from threading import RLock
from dataclasses import dataclass
from typing import Callable


def _canonical(node_id: str, nonce: str, issued_at: int, task_id: str, result_sha256: str) -> bytes:
    fields = (node_id, nonce, str(issued_at), task_id, result_sha256.lower())
    return "\n".join(fields).encode("utf-8")


def sign_node_response(secret: bytes, *, node_id: str, nonce: str, issued_at: int, task_id: str, result_sha256: str) -> str:
    """Create the HMAC proof a software node returns for a challenge and task result."""
    if not secret:
        raise ValueError("NODE_SECRET_REQUIRED")
    return hmac.new(secret, _canonical(node_id, nonce, issued_at, task_id, result_sha256), hashlib.sha256).hexdigest()


@dataclass(frozen=True)
class Challenge:
    node_id: str
    nonce: str
    issued_at: int
    expires_at: int


class SoftwareNodeIdentityGate:
    """Verify fresh challenge-response and task-result binding for software nodes.

    node_secrets must come from a trusted secret manager or protected environment,
    not from a request body or telemetry submitted by the node.
    """

    def __init__(self, node_secrets: dict[str, bytes], *, ttl_seconds: int = 90,
                 clock: Callable[[], float] = time.time,
                 nonce_factory: Callable[[], str] = lambda: secrets.token_urlsafe(32)) -> None:
        if ttl_seconds < 1:
            raise ValueError("TTL_MUST_BE_POSITIVE")
        self._secrets = dict(node_secrets)
        self._ttl = ttl_seconds
        self._clock = clock
        self._nonce_factory = nonce_factory
        self._pending: dict[str, Challenge] = {}
        self._consumed: set[str] = set()
        # Process-local synchronization only; durable cross-process replay protection
        # remains the responsibility of the central cloud-executor registry.
        self._lock = RLock()

    def issue_challenge(self, node_id: str) -> dict[str, object]:
        if not isinstance(node_id, str) or not node_id.strip():
            raise ValueError("NODE_ID_REQUIRED")
        if node_id not in self._secrets or not self._secrets[node_id]:
            raise PermissionError("NODE_IDENTITY_NOT_CONFIGURED")
        now = int(self._clock())
        nonce = self._nonce_factory()
        with self._lock:
            if not nonce or nonce in self._pending or nonce in self._consumed:
                raise RuntimeError("CHALLENGE_NONCE_COLLISION")
            challenge = Challenge(node_id, nonce, now, now + self._ttl)
            self._pending[nonce] = challenge
        return {"node_id": node_id, "nonce": nonce, "issued_at": now,
                "expires_at": challenge.expires_at, "challenge_status": "ISSUED",
                "claim_scope": "SOFTWARE_NODE_POSSESSION_PROOF"}

    def verify_response(self, *, node_id: str, nonce: str, issued_at: int,
                        task_id: str, result_sha256: str, signature: str) -> dict[str, object]:
        with self._lock:
            challenge = self._pending.get(nonce)
            if challenge is None or nonce in self._consumed:
                return self._blocked("CHALLENGE_UNKNOWN_OR_REPLAYED")
            now = int(self._clock())
            if now >= challenge.expires_at:
                self._pending.pop(nonce, None)
                self._consumed.add(nonce)
                return self._blocked("CHALLENGE_EXPIRED")
            if (node_id != challenge.node_id or issued_at != challenge.issued_at
                    or not isinstance(task_id, str) or not task_id.strip()
                    or not isinstance(result_sha256, str) or len(result_sha256) != 64
                    or any(c not in "0123456789abcdefABCDEF" for c in result_sha256)):
                return self._blocked("RESPONSE_FIELDS_INVALID")
            expected = sign_node_response(self._secrets[node_id], node_id=node_id, nonce=nonce,
                                          issued_at=issued_at, task_id=task_id, result_sha256=result_sha256)
            if not hmac.compare_digest(expected, str(signature).lower()):
                return self._blocked("IDENTITY_PROOF_INVALID")
            self._pending.pop(nonce, None)
            self._consumed.add(nonce)
            return {"status": "SOFTWARE_NODE_VERIFIED", "node_id": node_id,
                    "identity_verified": True, "fresh_challenge_verified": True,
                    "task_result_bound": True, "task_id": task_id,
                    "result_sha256": result_sha256.lower(), "verified_at": now,
                    "claim_scope": "SOFTWARE_NODE_ONLY", "physical_hardware_verified": False,
                    "independent_host_attestation_verified": False}

    @staticmethod
    def _blocked(reason: str) -> dict[str, object]:
        return {"status": "BLOCKED", "identity_verified": False,
                "physical_hardware_verified": False, "reason": reason}
