"""Persistent SQLite store for BRAIN-ASIC-001 identity records.

Local-first, zero-cost persistence. Database defaults to .brain/asic_identity.sqlite3
under the project root; override with BRAIN_ASIC_DB or --db. Do not store secrets.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from brain_v12.asic.unit_001.identity_registry import normalize_identity

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB = PROJECT_ROOT / ".brain" / "asic_identity.sqlite3"
SCHEMA_VERSION = 1


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ASICIdentityStore:
    """Small SQLite repository with explicit upsert and retrieval operations."""

    def __init__(self, db_path: str | Path | None = None):
        configured = db_path or os.environ.get("BRAIN_ASIC_DB") or DEFAULT_DB
        self.db_path = Path(configured).expanduser()

    def connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 10000")
        return conn

    def init(self) -> None:
        with self.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS asic_identity_records (
                    product_id TEXT PRIMARY KEY,
                    schema_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    identity_complete INTEGER NOT NULL CHECK(identity_complete IN (0, 1)),
                    physical_hardware_verified INTEGER NOT NULL
                        CHECK(physical_hardware_verified IN (0, 1)),
                    connection_verified INTEGER NOT NULL CHECK(connection_verified IN (0, 1)),
                    mining_live_verified INTEGER NOT NULL CHECK(mining_live_verified IN (0, 1)),
                    manufacturer TEXT,
                    device_model TEXT,
                    chip_part_number TEXT,
                    board_model TEXT,
                    manufacturer_serial_number TEXT,
                    connection_json TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    record_json TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL
                )
            """)
            conn.execute(
                "INSERT INTO schema_meta(key, value) VALUES('schema_version', ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(SCHEMA_VERSION),),
            )

    def save(self, raw_record: dict[str, Any]) -> dict[str, Any]:
        record = normalize_identity(raw_record)
        now = utc_now()
        product_id = record["brain_product_id"]
        with self.connect() as conn:
            conn.execute("""
                INSERT INTO asic_identity_records (
                    product_id, schema_name, status, identity_complete,
                    physical_hardware_verified, connection_verified, mining_live_verified,
                    manufacturer, device_model, chip_part_number, board_model,
                    manufacturer_serial_number, connection_json, evidence_json, record_json,
                    created_at_utc, updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(product_id) DO UPDATE SET
                    schema_name=excluded.schema_name,
                    status=excluded.status,
                    identity_complete=excluded.identity_complete,
                    physical_hardware_verified=excluded.physical_hardware_verified,
                    connection_verified=excluded.connection_verified,
                    mining_live_verified=excluded.mining_live_verified,
                    manufacturer=excluded.manufacturer,
                    device_model=excluded.device_model,
                    chip_part_number=excluded.chip_part_number,
                    board_model=excluded.board_model,
                    manufacturer_serial_number=excluded.manufacturer_serial_number,
                    connection_json=excluded.connection_json,
                    evidence_json=excluded.evidence_json,
                    record_json=excluded.record_json,
                    updated_at_utc=excluded.updated_at_utc
            """, (
                product_id, record["schema"], record["status"],
                int(record["identity_complete"]), int(record["physical_hardware_verified"]),
                int(record["connection_verified"]), int(record["mining_live_verified"]),
                record["manufacturer"], record["device_model"], record["chip_part_number"],
                record["board_model"], record["manufacturer_serial_number"],
                json.dumps(record["connection"], ensure_ascii=False, sort_keys=True),
                json.dumps(record["evidence"], ensure_ascii=False, sort_keys=True),
                json.dumps(record, ensure_ascii=False, sort_keys=True),
                now, now,
            ))
        return self.get(product_id) or {}

    def get(self, product_id: str = "BRAIN-ASIC-001") -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT record_json FROM asic_identity_records WHERE product_id = ?",
                (product_id,),
            ).fetchone()
        return json.loads(row["record_json"]) if row else None

    def list_records(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT record_json FROM asic_identity_records ORDER BY product_id"
            ).fetchall()
        return [json.loads(row["record_json"]) for row in rows]

    def health(self) -> dict[str, Any]:
        self.init()
        with self.connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM asic_identity_records").fetchone()[0]
            version = conn.execute(
                "SELECT value FROM schema_meta WHERE key='schema_version'"
            ).fetchone()[0]
        return {
            "database": str(self.db_path),
            "schema_version": int(version),
            "record_count": count,
            "status": "SQLITE_READY",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Store and retrieve ASIC identity records in SQLite")
    parser.add_argument("--db", type=Path, default=None, help="database path (or BRAIN_ASIC_DB)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="initialize the database")
    commands.add_parser("health", help="show database readiness")
    commands.add_parser("get", help="retrieve BRAIN-ASIC-001 identity")
    commands.add_parser("list", help="list stored identity records")
    save = commands.add_parser("save", help="save identity JSON from a file")
    save.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    store = ASICIdentityStore(args.db)
    if args.command == "init":
        store.init()
        result: Any = store.health()
    elif args.command == "health":
        result = store.health()
    elif args.command == "get":
        store.init()
        result = store.get()
    elif args.command == "list":
        store.init()
        result = store.list_records()
    else:
        raw = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            parser.error("input JSON must be an object")
        store.init()
        result = store.save(raw)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
