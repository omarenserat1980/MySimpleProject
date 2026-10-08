"""Single-active Brain leadership lease with fencing tokens.

This is a durable single-host control-plane primitive. It intentionally does
NOT claim distributed consensus: for multi-VM Brain deployments the backing
store must be shared/transactional. A recovered Brain must bind leadership to
its validated identity/checkpoint before it can execute consequential work.
"""
from __future__ import annotations

import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .brain_identity import require_checkpoint_identity


@dataclass(frozen=True)
class LeadershipLease:
    brain_id: str
    generation: int
    lease_id: str
    fencing_token: int
    holder_id: str
    acquired_at: float
    expires_at: float


class BrainLeadershipStore:
    def __init__(self, path: str | Path = "brain6_artifacts/control_plane/leadership.db"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS leadership(
              singleton INTEGER PRIMARY KEY CHECK(singleton=1),
              brain_id TEXT NOT NULL,
              generation INTEGER NOT NULL,
              lease_id TEXT NOT NULL UNIQUE,
              fencing_token INTEGER NOT NULL,
              holder_id TEXT NOT NULL,
              acquired_at REAL NOT NULL,
              expires_at REAL NOT NULL
            )"""
        )

    @staticmethod
    def _valid_identity(identity: dict[str, Any], checkpoint: dict[str, Any]) -> dict[str, Any]:
        return require_checkpoint_identity(identity, checkpoint)

    def acquire(
        self,
        identity: dict[str, Any],
        checkpoint: dict[str, Any],
        holder_id: str,
        *,
        lease_seconds: int = 300,
        now: float | None = None,
    ) -> LeadershipLease:
        verified = self._valid_identity(identity, checkpoint)
        holder_id = str(holder_id).strip()
        if not holder_id:
            raise ValueError("BRAIN_LEADERSHIP_HOLDER_REQUIRED")
        now = time.time() if now is None else float(now)
        expires = now + max(5, int(lease_seconds))
        lease_id = uuid.uuid4().hex

        try:
            self.db.execute("BEGIN IMMEDIATE")
            row = self.db.execute("SELECT * FROM leadership WHERE singleton=1").fetchone()
            if row is not None and float(row["expires_at"]) > now:
                raise RuntimeError("BRAIN_LEADERSHIP_HELD")

            next_token = (int(row["fencing_token"]) + 1) if row else 1
            self.db.execute("DELETE FROM leadership WHERE singleton=1")
            self.db.execute(
                """INSERT INTO leadership
                   (singleton,brain_id,generation,lease_id,fencing_token,holder_id,acquired_at,expires_at)
                   VALUES(1,?,?,?,?,?,?,?)""",
                (verified["brain_id"], verified["generation"], lease_id,
                 next_token, holder_id, now, expires),
            )
            self.db.execute("COMMIT")
        except Exception:
            try:
                self.db.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise

        return LeadershipLease(
            verified["brain_id"], verified["generation"], lease_id, next_token,
            holder_id, now, expires
        )

    def renew(self, lease: LeadershipLease, *, lease_seconds: int = 300, now: float | None = None) -> LeadershipLease:
        now = time.time() if now is None else float(now)
        expires = now + max(5, int(lease_seconds))
        cur = self.db.execute(
            """UPDATE leadership SET expires_at=?
               WHERE singleton=1 AND lease_id=? AND fencing_token=?
                 AND holder_id=? AND brain_id=? AND generation=? AND expires_at>?""",
            (expires, lease.lease_id, lease.fencing_token, lease.holder_id,
             lease.brain_id, lease.generation, now),
        )
        if cur.rowcount != 1:
            raise RuntimeError("BRAIN_LEADERSHIP_RENEW_REJECTED")
        return LeadershipLease(lease.brain_id, lease.generation, lease.lease_id,
                               lease.fencing_token, lease.holder_id,
                               lease.acquired_at, expires)

    def release(self, lease: LeadershipLease) -> bool:
        cur = self.db.execute(
            """DELETE FROM leadership
               WHERE singleton=1 AND lease_id=? AND fencing_token=? AND holder_id=?""",
            (lease.lease_id, lease.fencing_token, lease.holder_id),
        )
        return cur.rowcount == 1

    def status(self, *, now: float | None = None) -> dict[str, Any]:
        now = time.time() if now is None else float(now)
        row = self.db.execute("SELECT * FROM leadership WHERE singleton=1").fetchone()
        if row is None:
            return {"active": False, "status": "NO_LEADER"}
        item = dict(row)
        item["active"] = float(item["expires_at"]) > now
        item["status"] = "ACTIVE" if item["active"] else "EXPIRED"
        return item

    def assert_current(self, lease: LeadershipLease, *, now: float | None = None) -> dict[str, Any]:
        now = time.time() if now is None else float(now)
        row = self.db.execute("SELECT * FROM leadership WHERE singleton=1").fetchone()
        if row is None or float(row["expires_at"]) <= now:
            raise RuntimeError("BRAIN_LEADERSHIP_NOT_ACTIVE")
        for key, value in (
            ("lease_id", lease.lease_id),
            ("fencing_token", lease.fencing_token),
            ("holder_id", lease.holder_id),
            ("brain_id", lease.brain_id),
            ("generation", lease.generation),
        ):
            if row[key] != value:
                raise RuntimeError("BRAIN_LEADERSHIP_FENCED")
        return {"verified": True, "fencing_token": lease.fencing_token}

    def close(self) -> None:
        self.db.close()
