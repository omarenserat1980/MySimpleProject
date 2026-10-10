"""Evidence-first inventory of software managed by Electronic Brain.

This module records software metadata only. It never installs, launches, updates,
or removes software. Runtime lifecycle operations must be implemented separately
behind an explicit approval and execution policy.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SOFTWARE_STATES = {"planned", "observed", "installed", "running", "stopped", "failed", "unknown"}
VERIFICATION_STATES = {"unverified", "verified", "failed"}
SOFTWARE_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}$")
REQUIRED_TEXT = ("name", "category", "version", "source", "license")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SoftwareRegistry:
    """SQLite-backed inventory with provenance and explicit verification evidence."""

    def __init__(self, db_path: str | os.PathLike[str]):
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path, timeout=10)
        con.row_factory = sqlite3.Row
        return con

    def _initialize(self) -> None:
        with self._connect() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS brain_software_registry (
                    software_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    version TEXT NOT NULL,
                    source TEXT NOT NULL,
                    license TEXT NOT NULL,
                    install_path TEXT,
                    runtime_state TEXT NOT NULL,
                    verification_state TEXT NOT NULL,
                    permissions_json TEXT NOT NULL,
                    evidence_ref TEXT,
                    notes TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            con.execute("CREATE INDEX IF NOT EXISTS idx_brain_software_category ON brain_software_registry(category)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_brain_software_state ON brain_software_registry(runtime_state)")

    @staticmethod
    def _serialize(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["permissions"] = json.loads(item.pop("permissions_json"))
        return item

    def register(self, software_id: str, metadata: dict[str, Any]) -> dict[str, Any]:
        """Register a planned/observed item; do not treat registration as installation."""
        if not isinstance(software_id, str) or not SOFTWARE_ID_RE.fullmatch(software_id):
            raise ValueError("INVALID_SOFTWARE_ID")
        if not isinstance(metadata, dict):
            raise ValueError("METADATA_MUST_BE_OBJECT")
        values: dict[str, str] = {}
        for key in REQUIRED_TEXT:
            value = metadata.get(key)
            if not isinstance(value, str) or not value.strip() or len(value) > 512:
                raise ValueError(f"INVALID_{key.upper()}")
            values[key] = value.strip()
        state = metadata.get("runtime_state", "planned")
        if state not in {"planned", "observed", "unknown"}:
            raise ValueError("REGISTRATION_STATE_MUST_BE_PLANNED_OBSERVED_OR_UNKNOWN")
        permissions = metadata.get("permissions", [])
        if not isinstance(permissions, list) or len(permissions) > 64 or not all(
            isinstance(p, str) and 0 < len(p) <= 128 for p in permissions
        ):
            raise ValueError("INVALID_PERMISSIONS")
        install_path = metadata.get("install_path")
        if install_path is not None and (not isinstance(install_path, str) or len(install_path) > 1024):
            raise ValueError("INVALID_INSTALL_PATH")
        notes = metadata.get("notes", "")
        if not isinstance(notes, str) or len(notes) > 4000:
            raise ValueError("INVALID_NOTES")
        now = _now()
        with self._connect() as con:
            existing = con.execute(
                "SELECT created_at FROM brain_software_registry WHERE software_id=?", (software_id,)
            ).fetchone()
            created_at = existing["created_at"] if existing else now
            con.execute("""
                INSERT INTO brain_software_registry
                (software_id,name,category,version,source,license,install_path,runtime_state,
                 verification_state,permissions_json,evidence_ref,notes,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(software_id) DO UPDATE SET
                  name=excluded.name, category=excluded.category, version=excluded.version,
                  source=excluded.source, license=excluded.license, install_path=excluded.install_path,
                  runtime_state=excluded.runtime_state, permissions_json=excluded.permissions_json,
                  notes=excluded.notes, updated_at=excluded.updated_at
            """, (
                software_id, values["name"], values["category"], values["version"],
                values["source"], values["license"], install_path, state, "unverified",
                json.dumps(permissions), None, notes, created_at, now
            ))
            row = con.execute("SELECT * FROM brain_software_registry WHERE software_id=?", (software_id,)).fetchone()
            return self._serialize(row)

    def record_observation(
        self, software_id: str, runtime_state: str, verification_state: str,
        evidence_ref: str, install_path: str | None = None, notes: str | None = None,
    ) -> dict[str, Any]:
        """Record externally obtained evidence; never runs a probe or trusts empty evidence."""
        if runtime_state not in SOFTWARE_STATES:
            raise ValueError("INVALID_RUNTIME_STATE")
        if verification_state not in VERIFICATION_STATES:
            raise ValueError("INVALID_VERIFICATION_STATE")
        if not isinstance(evidence_ref, str) or not evidence_ref.strip() or len(evidence_ref) > 2048:
            raise ValueError("EVIDENCE_REFERENCE_REQUIRED")
        if verification_state == "verified" and runtime_state not in {"observed", "installed", "running", "stopped"}:
            raise ValueError("VERIFIED_STATE_REQUIRES_OBSERVED_OR_INSTALLED_RUNTIME")
        now = _now()
        with self._connect() as con:
            row = con.execute("SELECT * FROM brain_software_registry WHERE software_id=?", (software_id,)).fetchone()
            if row is None:
                raise KeyError("SOFTWARE_NOT_FOUND")
            con.execute("""
                UPDATE brain_software_registry
                SET runtime_state=?, verification_state=?, evidence_ref=?,
                    install_path=COALESCE(?, install_path), notes=COALESCE(?, notes), updated_at=?
                WHERE software_id=?
            """, (runtime_state, verification_state, evidence_ref.strip(), install_path, notes, now, software_id))
            return self._serialize(con.execute(
                "SELECT * FROM brain_software_registry WHERE software_id=?", (software_id,)
            ).fetchone())

    def get(self, software_id: str) -> dict[str, Any] | None:
        with self._connect() as con:
            row = con.execute("SELECT * FROM brain_software_registry WHERE software_id=?", (software_id,)).fetchone()
            return self._serialize(row) if row else None

    def list(self, category: str | None = None, runtime_state: str | None = None) -> list[dict[str, Any]]:
        clauses, params = [], []
        if category:
            clauses.append("category=?")
            params.append(category)
        if runtime_state:
            if runtime_state not in SOFTWARE_STATES:
                raise ValueError("INVALID_RUNTIME_STATE")
            clauses.append("runtime_state=?")
            params.append(runtime_state)
        sql = "SELECT * FROM brain_software_registry"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY category, name, software_id"
        with self._connect() as con:
            return [self._serialize(row) for row in con.execute(sql, params).fetchall()]

    def summary(self) -> dict[str, Any]:
        with self._connect() as con:
            total = con.execute("SELECT COUNT(*) FROM brain_software_registry").fetchone()[0]
            by_state = {
                row["runtime_state"]: row["count"]
                for row in con.execute(
                    "SELECT runtime_state, COUNT(*) AS count FROM brain_software_registry GROUP BY runtime_state"
                ).fetchall()
            }
            unverified = con.execute(
                "SELECT COUNT(*) FROM brain_software_registry WHERE verification_state != 'verified'"
            ).fetchone()[0]
        return {
            "ok": True,
            "component": "software_registry",
            "total": total,
            "by_runtime_state": by_state,
            "unverified": unverified,
            "execution_enabled": False,
            "note": "Inventory only; registration does not install or execute software."
        }
