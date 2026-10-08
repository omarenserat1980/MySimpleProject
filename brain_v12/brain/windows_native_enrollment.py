"""Cryptographic enrollment and replay-resistant attestation for native Windows nodes."""
from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
import time
from dataclasses import dataclass
from typing import Any


WINDOWS_NATIVE_ATTESTATION_V1 = "windows-native-attestation-v1"


def _canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def attestation_digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(payload)).hexdigest()


def verify_attestation(*, payload: dict[str, Any], signature: str, signing_token: str) -> bool:
    if not signing_token or not signature:
        return False
    expected = hmac.new(signing_token.encode(), _canonical(payload), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


class AttestationReplayGuard:
    """Durable one-time challenge consumption.

    A challenge is accepted once and only once. Expired or previously consumed
    challenges fail closed. The database is intentionally separate from the
    execution evidence store.
    """

    def __init__(self, path: str = "brain6_artifacts/control_plane/windows_attestation_nonce.db"):
        self.db = sqlite3.connect(path, timeout=10, isolation_level=None)
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS challenges(
               challenge TEXT PRIMARY KEY,
               expires_at REAL NOT NULL,
               consumed_at REAL
            )"""
        )

    def issue(self, challenge: str, expires_at: float) -> None:
        if not challenge.strip() or expires_at <= time.time():
            raise ValueError("windows_native_challenge_invalid")
        self.db.execute(
            "INSERT INTO challenges(challenge,expires_at,consumed_at) VALUES(?,?,NULL)",
            (challenge, float(expires_at)),
        )

    def consume(self, challenge: str, *, now: float | None = None) -> None:
        now = time.time() if now is None else float(now)
        cur = self.db.execute(
            """UPDATE challenges SET consumed_at=?
               WHERE challenge=? AND consumed_at IS NULL AND expires_at>?""",
            (now, challenge, now),
        )
        if cur.rowcount != 1:
            raise PermissionError("WINDOWS_NATIVE_ATTESTATION_REPLAY_OR_EXPIRED")

    def close(self) -> None:
        self.db.close()


@dataclass(frozen=True)
class WindowsNativeEnrollment:
    enrollment_id: str
    executor_id: str
    server_id: str
    brain_id: str
    brain_generation: int
    network_generation: int
    challenge: str
    platform: str
    architecture: str
    challenge_expires_at: float = 0.0
    attestation_version: str = WINDOWS_NATIVE_ATTESTATION_V1

    def validate(self, *, now: float | None = None) -> None:
        for name, value in (
            ("enrollment_id", self.enrollment_id),
            ("executor_id", self.executor_id),
            ("server_id", self.server_id),
            ("brain_id", self.brain_id),
            ("challenge", self.challenge),
            ("platform", self.platform),
            ("architecture", self.architecture),
        ):
            if not str(value).strip():
                raise ValueError(f"windows_native_{name}_required")
        if self.brain_generation < 1:
            raise ValueError("windows_native_brain_generation_invalid")
        if self.network_generation < 1:
            raise ValueError("windows_native_network_generation_invalid")
        now = time.time() if now is None else float(now)
        if self.challenge_expires_at <= now:
            raise ValueError("windows_native_challenge_expired")
        if self.attestation_version != WINDOWS_NATIVE_ATTESTATION_V1:
            raise ValueError("windows_native_attestation_version_invalid")

    def attestation_payload(self) -> dict[str, Any]:
        self.validate()
        return {
            "schema": self.attestation_version,
            "enrollment_id": self.enrollment_id,
            "executor_id": self.executor_id,
            "server_id": self.server_id,
            "brain_id": self.brain_id,
            "brain_generation": self.brain_generation,
            "network_generation": self.network_generation,
            "challenge": self.challenge,
            "challenge_expires_at": self.challenge_expires_at,
            "platform": self.platform,
            "architecture": self.architecture,
        }

    def verify(
        self,
        signature: str,
        signing_token: str,
        replay_guard: AttestationReplayGuard | None = None,
        *,
        now: float | None = None,
    ) -> dict[str, Any]:
        payload = self.attestation_payload()
        verified = verify_attestation(payload=payload, signature=signature, signing_token=signing_token)
        if verified and replay_guard is not None:
            replay_guard.consume(self.challenge, now=now)
        return {
            "verified": verified,
            "schema": self.attestation_version,
            "enrollment_id": self.enrollment_id,
            "executor_id": self.executor_id,
            "server_id": self.server_id,
            "brain_generation": self.brain_generation,
            "network_generation": self.network_generation,
            "attestation_digest": attestation_digest(payload),
        }
