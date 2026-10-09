"""Durable ISO download lifecycle primitives.

This module deliberately does not fetch remote URLs or expose HTTP routes. It provides
transactional state transitions and safe server-owned storage paths for later integration
with Brain V12's authenticated control plane.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable
from uuid import uuid4

STATES = frozenset({
    "CREATED", "VALIDATING", "QUEUED", "CONNECTING", "DOWNLOADING",
    "PAUSE_REQUESTED", "PAUSED", "RETRY_WAIT", "VERIFYING", "COMPLETED",
    "CANCEL_REQUESTED", "CANCELLED", "FAILED", "INTERRUPTED",
    "RECOVERING", "EXPIRED",
})
FINAL_STATES = frozenset({"COMPLETED", "CANCELLED", "FAILED", "EXPIRED"})
ACTIVE_STATES = frozenset({
    "VALIDATING", "QUEUED", "CONNECTING", "DOWNLOADING", "PAUSE_REQUESTED",
    "RETRY_WAIT", "VERIFYING", "CANCEL_REQUESTED", "RECOVERING",
})
TRANSITIONS = {
    "CREATED": {"VALIDATING"},
    "VALIDATING": {"QUEUED", "FAILED", "CANCEL_REQUESTED"},
    "QUEUED": {"CONNECTING", "CANCEL_REQUESTED"},
    "CONNECTING": {"DOWNLOADING", "RETRY_WAIT", "CANCEL_REQUESTED"},
    "DOWNLOADING": {"PAUSE_REQUESTED", "RETRY_WAIT", "VERIFYING", "CANCEL_REQUESTED"},
    "PAUSE_REQUESTED": {"PAUSED", "CANCEL_REQUESTED", "INTERRUPTED"},
    "PAUSED": {"QUEUED", "CANCEL_REQUESTED", "EXPIRED"},
    "RETRY_WAIT": {"CONNECTING", "FAILED", "CANCEL_REQUESTED", "INTERRUPTED"},
    "VERIFYING": {"COMPLETED", "FAILED", "CANCEL_REQUESTED", "INTERRUPTED"},
    "CANCEL_REQUESTED": {"CANCELLED", "INTERRUPTED"},
    "INTERRUPTED": {"RECOVERING"},
    "RECOVERING": {"PAUSED", "QUEUED", "FAILED", "CANCEL_REQUESTED"},
    "COMPLETED": {"EXPIRED"},
    "CANCELLED": {"EXPIRED"},
    "FAILED": {"EXPIRED"},
    "EXPIRED": set(),
}


class DownloadError(ValueError):
    """Stable, non-secret download error contract."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class DownloadStore:
    """SQLite-backed lifecycle store; callers must supply a durable root explicitly."""

    def __init__(self, root: str | os.PathLike[str], *, persistent: bool):
        self.root = Path(root).expanduser().resolve()
        self.persistent = bool(persistent)
        self.metadata = self.root / "metadata"
        self.partial = self.root / "partial"
        self.completed = self.root / "completed"
        self.quarantine = self.root / "quarantine"
        for directory in (self.metadata, self.partial, self.completed, self.quarantine):
            directory.mkdir(parents=True, exist_ok=True)
        self.db_path = self.metadata / "downloads.sqlite3"
        self._initialize()

    @contextmanager
    def _db(self):
        conn = sqlite3.connect(str(self.db_path), timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=FULL")
            yield conn
        finally:
            conn.close()

    def _initialize(self):
        with self._db() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS downloads (
                download_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                state TEXT NOT NULL,
                source TEXT NOT NULL,
                expected_size INTEGER,
                expected_sha256 TEXT,
                bytes_written INTEGER NOT NULL DEFAULT 0,
                source_etag TEXT,
                source_last_modified TEXT,
                attempts INTEGER NOT NULL DEFAULT 0,
                worker_id TEXT,
                cleanup_result TEXT,
                cleanup_reason TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                last_request_id TEXT
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS transitions (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                download_id TEXT NOT NULL REFERENCES downloads(download_id),
                previous_state TEXT,
                new_state TEXT NOT NULL,
                occurred_at REAL NOT NULL,
                reason TEXT NOT NULL,
                request_id TEXT
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS worker_leases (
                download_id TEXT PRIMARY KEY REFERENCES downloads(download_id),
                worker_id TEXT NOT NULL,
                acquired_at REAL NOT NULL
            )""")

    def create(self, *, owner_id: str, source: str, expected_size: int | None = None,
               expected_sha256: str | None = None, resumable: bool = True,
               request_id: str | None = None) -> dict:
        if resumable and not self.persistent:
            raise DownloadError("PERSISTENT_STORAGE_REQUIRED")
        if not owner_id or not source:
            raise DownloadError("INVALID_REQUEST")
        if expected_size is not None and expected_size < 0:
            raise DownloadError("INVALID_REQUEST")
        if expected_sha256 is not None:
            digest = expected_sha256.lower()
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise DownloadError("INVALID_REQUEST")
            expected_sha256 = digest
        now = time.time()
        download_id = uuid4().hex
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("""INSERT INTO downloads
                (download_id,owner_id,state,source,expected_size,expected_sha256,
                 created_at,updated_at,last_request_id)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (download_id, owner_id, "CREATED", source, expected_size,
                 expected_sha256, now, now, request_id))
            db.execute("""INSERT INTO transitions
                (download_id,previous_state,new_state,occurred_at,reason,request_id)
                VALUES(?,?,?,?,?,?)""",
                (download_id, None, "CREATED", now, "task created", request_id))
            db.execute("COMMIT")
        return self.get(download_id, owner_id=owner_id)

    def get(self, download_id: str, *, owner_id: str) -> dict:
        with self._db() as db:
            row = db.execute(
                "SELECT * FROM downloads WHERE download_id=? AND owner_id=?",
                (download_id, owner_id)).fetchone()
        if row is None:
            raise DownloadError("TASK_NOT_FOUND")
        return dict(row)

    def transition(self, download_id: str, *, owner_id: str, new_state: str,
                   reason: str, request_id: str | None = None,
                   idempotent: bool = False) -> dict:
        if new_state not in STATES:
            raise DownloadError("INVALID_STATE_TRANSITION")
        now = time.time()
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM downloads WHERE download_id=? AND owner_id=?",
                (download_id, owner_id)).fetchone()
            if row is None:
                db.execute("ROLLBACK")
                raise DownloadError("TASK_NOT_FOUND")
            previous = row["state"]
            if previous == new_state and idempotent:
                db.execute("COMMIT")
                return dict(row)
            if new_state not in TRANSITIONS.get(previous, set()):
                db.execute("ROLLBACK")
                raise DownloadError("INVALID_STATE_TRANSITION")
            db.execute("""UPDATE downloads SET state=?,updated_at=?,last_request_id=?
                WHERE download_id=? AND state=?""",
                (new_state, now, request_id, download_id, previous))
            if db.execute("SELECT changes()").fetchone()[0] != 1:
                db.execute("ROLLBACK")
                raise DownloadError("TASK_CONFLICT")
            db.execute("""INSERT INTO transitions
                (download_id,previous_state,new_state,occurred_at,reason,request_id)
                VALUES(?,?,?,?,?,?)""",
                (download_id, previous, new_state, now, reason[:200], request_id))
            db.execute("COMMIT")
        return self.get(download_id, owner_id=owner_id)

    def acquire_worker(self, download_id: str, *, worker_id: str) -> bool:
        """Atomically allow one writer lease per task."""
        if not worker_id:
            raise DownloadError("INVALID_REQUEST")
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            exists = db.execute(
                "SELECT 1 FROM downloads WHERE download_id=?", (download_id,)).fetchone()
            if not exists:
                db.execute("ROLLBACK")
                raise DownloadError("TASK_NOT_FOUND")
            try:
                db.execute("INSERT INTO worker_leases VALUES(?,?,?)",
                           (download_id, worker_id, time.time()))
            except sqlite3.IntegrityError:
                db.execute("ROLLBACK")
                return False
            db.execute("COMMIT")
            return True

    def release_worker(self, download_id: str, *, worker_id: str) -> bool:
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM worker_leases WHERE download_id=? AND worker_id=?",
                       (download_id, worker_id))
            changed = db.execute("SELECT changes()").fetchone()[0] == 1
            db.execute("COMMIT")
            return changed

    def transition_history(self, download_id: str, *, owner_id: str) -> list[dict]:
        self.get(download_id, owner_id=owner_id)
        with self._db() as db:
            rows = db.execute("""SELECT previous_state,new_state,occurred_at,reason,request_id
                FROM transitions WHERE download_id=? ORDER BY event_id""",
                (download_id,)).fetchall()
        return [dict(row) for row in rows]

    def server_path(self, download_id: str, *, area: str, suffix: str = ".part") -> Path:
        if not download_id or any(c not in "0123456789abcdef" for c in download_id.lower()):
            raise DownloadError("INVALID_REQUEST")
        bases = {"partial": self.partial, "completed": self.completed,
                 "quarantine": self.quarantine}
        if area not in bases or suffix not in (".part", ".iso", ".bin"):
            raise DownloadError("INVALID_REQUEST")
        base = bases[area].resolve()
        # Inspect the lexical entry before resolving it: Path.resolve() follows a
        # symlink, making a later is_symlink() check on the resolved target ineffective.
        candidate = base / f"{download_id}{suffix}"
        if candidate.is_symlink():
            raise DownloadError("INVALID_STORAGE_PATH")
        target = candidate.resolve()
        if target.parent != base:
            raise DownloadError("INVALID_STORAGE_PATH")
        # Reject a target that appeared as a symlink between the first check and
        # resolution. Callers must still use safe open flags to close TOCTOU windows.
        if target.is_symlink():
            raise DownloadError("INVALID_STORAGE_PATH")
        return target

    def record_cleanup(self, download_id: str, *, owner_id: str,
                       result: str, reason: str) -> None:
        if result not in {"CLEANED", "RETAINED", "CLEANUP_FAILED"}:
            raise DownloadError("INVALID_REQUEST")
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            cur = db.execute("""UPDATE downloads SET cleanup_result=?,cleanup_reason=?,updated_at=?
                WHERE download_id=? AND owner_id=?""",
                (result, reason[:200], time.time(), download_id, owner_id))
            if cur.rowcount != 1:
                db.execute("ROLLBACK")
                raise DownloadError("TASK_NOT_FOUND")
            db.execute("COMMIT")
