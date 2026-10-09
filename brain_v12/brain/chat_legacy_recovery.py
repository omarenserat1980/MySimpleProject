"""Fail-closed inventory and explicit recovery for unowned legacy Brain Chat sessions.

Inventory is read-only. Ownership changes require a reviewed JSON mapping and
an explicit confirmation phrase. This tool never infers ownership from content,
device IDs, or the requesting account.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

CONFIRM_PHRASE = "ASSIGN_EXPLICIT_OWNERSHIP"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect_existing(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    if not path.is_file():
        raise FileNotFoundError(f"Database file does not exist: {path}")
    con = sqlite3.connect(str(path), timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def inventory(db_path: str | Path) -> dict:
    """Return a privacy-preserving inventory without modifying the database."""
    with _connect_existing(db_path) as con:
        columns = {row["name"] for row in con.execute("PRAGMA table_info(chat_sessions)")}
        if not columns or not {"id", "account_id", "device_id", "title", "created_at", "updated_at"}.issubset(columns):
            raise RuntimeError("CHAT_SESSIONS_SCHEMA_UNSUPPORTED")
        rows = con.execute(
            """SELECT id, account_id, device_id, created_at, updated_at
               FROM chat_sessions WHERE account_id IS NULL OR trim(account_id)=''
               ORDER BY created_at, id"""
        ).fetchall()
        total = con.execute("SELECT COUNT(*) FROM chat_sessions").fetchone()[0]
    return {
        "schema": "brain-chat-legacy-inventory/v1",
        "generated_at": _now(),
        "database": str(Path(db_path).resolve()),
        "total_sessions": total,
        "unowned_count": len(rows),
        "unowned_sessions": [
            {key: row[key] for key in ("id", "device_id", "created_at", "updated_at")}
            for row in rows
        ],
        "note": "No message content is included. Inventory does not modify the database.",
    }


def apply_mapping(
    db_path: str | Path,
    mapping: Mapping[str, str],
    *,
    confirm: str,
    actor: str,
    reason: str,
) -> dict:
    """Atomically assign only explicitly mapped, currently unowned sessions."""
    if confirm != CONFIRM_PHRASE:
        raise ValueError("EXPLICIT_CONFIRMATION_REQUIRED")
    if not actor.strip() or not reason.strip():
        raise ValueError("ACTOR_AND_REASON_REQUIRED")
    if not mapping:
        raise ValueError("EMPTY_MAPPING")
    normalized: dict[str, str] = {}
    for session_id, account_id in mapping.items():
        sid, aid = str(session_id).strip(), str(account_id).strip()
        if not sid or not aid:
            raise ValueError("EMPTY_SESSION_OR_ACCOUNT_ID")
        if len(aid) > 200 or len(sid) > 200:
            raise ValueError("IDENTIFIER_TOO_LONG")
        normalized[sid] = aid

    now = _now()
    with _connect_existing(db_path) as con:
        con.execute("BEGIN IMMEDIATE")
        columns = {row["name"] for row in con.execute("PRAGMA table_info(chat_sessions)")}
        if not {"id", "account_id"}.issubset(columns):
            raise RuntimeError("CHAT_SESSIONS_SCHEMA_UNSUPPORTED")

        ids = list(normalized)
        placeholders = ",".join("?" for _ in ids)
        rows = con.execute(
            f"SELECT id, account_id FROM chat_sessions WHERE id IN ({placeholders})",
            ids,
        ).fetchall()
        found = {row["id"]: row["account_id"] for row in rows}
        missing = sorted(set(ids) - set(found))
        already_owned = sorted(sid for sid, owner in found.items() if owner is not None and str(owner).strip())
        if missing:
            raise ValueError("UNKNOWN_SESSION_IDS:" + ",".join(missing))
        if already_owned:
            raise ValueError("SESSIONS_ALREADY_OWNED:" + ",".join(already_owned))

        con.execute(
            """CREATE TABLE IF NOT EXISTS chat_session_ownership_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                previous_account_id TEXT,
                assigned_account_id TEXT NOT NULL,
                actor TEXT NOT NULL,
                reason TEXT NOT NULL,
                changed_at TEXT NOT NULL
            )"""
        )
        # Every row must still be unowned at write time. Any mismatch aborts the
        # transaction; no automatic account inference or reassignment is allowed.
        for session_id, account_id in normalized.items():
            cur = con.execute(
                """UPDATE chat_sessions SET account_id=?
                   WHERE id=? AND (account_id IS NULL OR trim(account_id)='')""",
                (account_id, session_id),
            )
            if cur.rowcount != 1:
                raise RuntimeError("OWNERSHIP_CHANGED_DURING_RECOVERY:" + session_id)
            con.execute(
                """INSERT INTO chat_session_ownership_audit
                   (session_id, previous_account_id, assigned_account_id, actor, reason, changed_at)
                   VALUES (?, NULL, ?, ?, ?, ?)""",
                (session_id, account_id, actor.strip(), reason.strip(), now),
            )
        con.commit()
    return {
        "schema": "brain-chat-legacy-recovery-result/v1",
        "applied": True,
        "changed_count": len(normalized),
        "changed_session_ids": sorted(normalized),
        "audit_table": "chat_session_ownership_audit",
        "changed_at": now,
        "warning": "Confirm account ownership from trusted evidence before applying.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="Exact SQLite database path used by Brain")
    sub = parser.add_subparsers(dest="command", required=True)
    inv = sub.add_parser("inventory", help="Read-only inventory of unowned sessions")
    inv.add_argument("--output", help="Optional JSON report path")
    apply = sub.add_parser("apply", help="Apply a reviewed session_id -> account_id JSON map")
    apply.add_argument("--mapping", required=True, help="JSON object mapping session IDs to verified account IDs")
    apply.add_argument("--confirm", required=True, help=f"Must equal {CONFIRM_PHRASE}")
    apply.add_argument("--actor", default=os.environ.get("USER", "operator"))
    apply.add_argument("--reason", required=True, help="Ticket/evidence reference for the ownership decision")
    args = parser.parse_args()

    if args.command == "inventory":
        result = inventory(args.db)
        rendered = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            Path(args.output).write_text(rendered + "\n", encoding="utf-8")
        print(rendered)
        return 0

    mapping_path = Path(args.mapping)
    data = json.loads(mapping_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("MAPPING_MUST_BE_JSON_OBJECT")
    result = apply_mapping(
        args.db, data, confirm=args.confirm, actor=args.actor, reason=args.reason
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
