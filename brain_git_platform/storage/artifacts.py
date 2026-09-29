from __future__ import annotations

import hashlib
import re
import sqlite3
from pathlib import Path

from .. import service

_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class ArtifactStore:
    """Brain-owned artifact storage with a durable metadata index."""

    def __init__(self, root: str | None = None):
        self.root = Path(root or (service.ROOT / "artifacts")).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / "artifacts.db"
        with sqlite3.connect(self.db) as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS artifacts(
                   run_id TEXT NOT NULL,
                   name TEXT NOT NULL,
                   sha256 TEXT NOT NULL,
                   size INTEGER NOT NULL,
                   created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                   PRIMARY KEY(run_id,name))"""
            )
            db.commit()

    @staticmethod
    def _safe(value: str, field: str) -> str:
        if not isinstance(value, str) or not _SAFE.fullmatch(value):
            raise ValueError(f"invalid {field}")
        return value

    def put(self, run_id: str, name: str, data: bytes) -> dict:
        run_id = self._safe(run_id, "run_id")
        name = self._safe(name, "artifact name")
        if not isinstance(data, bytes):
            raise TypeError("artifact data must be bytes")
        digest = hashlib.sha256(data).hexdigest()
        target = self.root / run_id / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        with sqlite3.connect(self.db) as db:
            db.execute(
                """INSERT INTO artifacts(run_id,name,sha256,size)
                   VALUES(?,?,?,?)
                   ON CONFLICT(run_id,name) DO UPDATE SET
                     sha256=excluded.sha256,size=excluded.size,created_at=CURRENT_TIMESTAMP""",
                (run_id, name, digest, len(data)),
            )
            db.commit()
        return {"run_id": run_id, "name": name, "sha256": digest, "size": len(data)}

    def get(self, run_id: str, name: str) -> bytes:
        run_id = self._safe(run_id, "run_id")
        name = self._safe(name, "artifact name")
        target = self.root / run_id / name
        if not target.exists():
            raise FileNotFoundError(name)
        return target.read_bytes()

    def metadata(self, run_id: str, name: str) -> dict:
        run_id = self._safe(run_id, "run_id")
        name = self._safe(name, "artifact name")
        with sqlite3.connect(self.db) as db:
            row = db.execute(
                "SELECT run_id,name,sha256,size,created_at FROM artifacts WHERE run_id=? AND name=?",
                (run_id, name),
            ).fetchone()
        if not row:
            raise FileNotFoundError(name)
        return {
            "run_id": row[0],
            "name": row[1],
            "sha256": row[2],
            "size": row[3],
            "created_at": row[4],
        }

    def list(self, run_id: str) -> list[dict]:
        run_id = self._safe(run_id, "run_id")
        with sqlite3.connect(self.db) as db:
            rows = db.execute(
                "SELECT run_id,name,sha256,size,created_at FROM artifacts WHERE run_id=? ORDER BY name",
                (run_id,),
            ).fetchall()
        return [
            {"run_id": r[0], "name": r[1], "sha256": r[2], "size": r[3], "created_at": r[4]}
            for r in rows
        ]
