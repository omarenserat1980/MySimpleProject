"""SQLite-backed, atomic one-time GEN challenge registry.

Use a persistent local database path for restart survival. For multi-host
deployments, use a shared transactional store with equivalent atomic semantics.
This module issues challenges only; it does not contact or attest hardware.
"""
from __future__ import annotations

import secrets
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class GENChallenge:
    nonce: str
    issuer_id: str
    subject_id: str
    subject_type: str
    operation: str
    issued_at: float
    expires_at: float


class GENChallengeRegistry:
    """Persist challenges and atomically consume a nonce at most once."""

    def __init__(
        self,
        database_path: str,
        *,
        ttl_seconds: int = 120,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if not isinstance(database_path, str) or not database_path.strip():
            raise ValueError("GEN_CHALLENGE_DATABASE_REQUIRED")
        if database_path == ":memory:":
            raise ValueError("GEN_CHALLENGE_DATABASE_MUST_BE_PERSISTENT")
        if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int) or not 1 <= ttl_seconds <= 300:
            raise ValueError("GEN_CHALLENGE_TTL_INVALID")
        self._path = database_path
        self._ttl = ttl_seconds
        self._clock = clock
        if database_path != ":memory:":
            Path(database_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS gen_challenges (
                    nonce TEXT PRIMARY KEY,
                    issuer_id TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    subject_type TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    issued_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                )
            """)
            db.execute("CREATE INDEX IF NOT EXISTS idx_gen_challenges_expiry ON gen_challenges(expires_at)")

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self._path, timeout=10, isolation_level=None)
        db.execute("PRAGMA busy_timeout=10000")
        return db

    def issue(self, *, issuer_id: str, subject_id: str, subject_type: str, operation: str) -> GENChallenge:
        for name, value in (("issuer_id", issuer_id), ("subject_id", subject_id),
                            ("subject_type", subject_type), ("operation", operation)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("GEN_CHALLENGE_FIELD_REQUIRED:" + name)
        if subject_type not in {"ASIC_DEVICE", "HOSTED_ASIC"}:
            raise ValueError("GEN_CHALLENGE_SUBJECT_TYPE_INVALID")
        now = float(self._clock())
        challenge = GENChallenge(
            nonce=secrets.token_urlsafe(32),
            issuer_id=issuer_id,
            subject_id=subject_id,
            subject_type=subject_type,
            operation=operation,
            issued_at=now,
            expires_at=now + self._ttl,
        )
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM gen_challenges WHERE expires_at <= ?", (now,))
            db.execute(
                """INSERT INTO gen_challenges
                   (nonce, issuer_id, subject_id, subject_type, operation, issued_at, expires_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (challenge.nonce, issuer_id, subject_id, subject_type, operation, now, challenge.expires_at),
            )
            db.commit()
        return challenge

    def consume(self, *, nonce: str, issuer_id: str, subject_id: str,
                subject_type: str, operation: str) -> GENChallenge:
        if not isinstance(nonce, str) or not nonce:
            raise ValueError("GEN_CHALLENGE_UNKNOWN_OR_REPLAYED")
        now = float(self._clock())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                """SELECT issuer_id, subject_id, subject_type, operation, issued_at, expires_at
                   FROM gen_challenges WHERE nonce = ?""",
                (nonce,),
            ).fetchone()
            if row is None:
                db.rollback()
                raise ValueError("GEN_CHALLENGE_UNKNOWN_OR_REPLAYED")
            # Consume before validating scope so a mismatched request cannot retry it.
            db.execute("DELETE FROM gen_challenges WHERE nonce = ?", (nonce,))
            db.commit()
        saved_issuer, saved_subject, saved_type, saved_operation, issued_at, expires_at = row
        if expires_at <= now:
            raise ValueError("GEN_CHALLENGE_EXPIRED")
        if (issuer_id, subject_id, subject_type, operation) != (
            saved_issuer, saved_subject, saved_type, saved_operation
        ):
            raise ValueError("GEN_CHALLENGE_SCOPE_MISMATCH")
        return GENChallenge(nonce, saved_issuer, saved_subject, saved_type,
                            saved_operation, issued_at, expires_at)


__all__ = ["GENChallenge", "GENChallengeRegistry"]
