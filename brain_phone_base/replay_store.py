#!/usr/bin/env python3
"""Durable, atomic one-time challenge ledger for Brain Phone Base.

This is a replay-control primitive, not an identity or hardware-attestation
verifier. Keep the database on trusted verifier-side storage with restrictive
filesystem permissions and backups appropriate to the deployment.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Final

_SCHEMA: Final[str] = """
CREATE TABLE IF NOT EXISTS consumed_challenges (
    challenge_id TEXT PRIMARY KEY NOT NULL,
    expires_at_utc TEXT NOT NULL,
    consumed_at_utc TEXT NOT NULL
)
"""


class ReplayStoreError(RuntimeError):
    """A fail-closed replay ledger error."""

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code


class SQLiteReplayStore:
    """Persist challenge consumption with a transaction and unique challenge ID."""

    def __init__(self, database_path: str | Path) -> None:
        raw_path = str(database_path)
        self.database_path = raw_path if raw_path == ":memory:" else str(Path(raw_path).expanduser())
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            with closing(self._connect()) as connection:
                connection.execute(_SCHEMA)
            if self.database_path != ":memory:":
                Path(self.database_path).chmod(0o600)
        except (OSError, sqlite3.Error) as exc:
            raise ReplayStoreError("REPLAY_STORE_UNAVAILABLE") from exc

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=5.0, isolation_level=None)
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    def consume(self, challenge_id: str, expires_at_utc: str, consumed_at_utc: str) -> None:
        """Atomically mark a challenge consumed; duplicate IDs always fail."""
        if not isinstance(challenge_id, str) or not challenge_id.strip() or len(challenge_id) > 256:
            raise ReplayStoreError("CHALLENGE_ID_INVALID")
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                try:
                    connection.execute(
                        "INSERT INTO consumed_challenges (challenge_id, expires_at_utc, consumed_at_utc) VALUES (?, ?, ?)",
                        (challenge_id, expires_at_utc, consumed_at_utc),
                    )
                    connection.execute("COMMIT")
                except sqlite3.IntegrityError as exc:
                    connection.execute("ROLLBACK")
                    raise ReplayStoreError("CHALLENGE_REPLAYED") from exc
                except Exception:
                    connection.execute("ROLLBACK")
                    raise
        except ReplayStoreError:
            raise
        except sqlite3.Error as exc:
            raise ReplayStoreError("REPLAY_STORE_UNAVAILABLE") from exc

    def contains(self, challenge_id: str) -> bool:
        """Read-only helper intended for diagnostics and tests."""
        try:
            with closing(self._connect()) as connection:
                row = connection.execute(
                    "SELECT 1 FROM consumed_challenges WHERE challenge_id = ?", (challenge_id,)
                ).fetchone()
                return row is not None
        except sqlite3.Error as exc:
            raise ReplayStoreError("REPLAY_STORE_UNAVAILABLE") from exc
