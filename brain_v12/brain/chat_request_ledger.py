"""Durable idempotency ledger for Brain Chat message requests."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ChatRequestLedger:
    """Serializes requests by (session_id, client_message_id) across workers."""

    def __init__(self, path="brain_v12.db"):
        self.path = Path(path)

    def connect(self):
        con = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        con.row_factory = sqlite3.Row
        return con

    def init(self):
        with self.connect() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS chat_request_idempotency (
                    session_id TEXT NOT NULL,
                    client_message_id TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    response_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (session_id, client_message_id)
                )
            """)
            con.execute("CREATE INDEX IF NOT EXISTS idx_chat_request_status ON chat_request_idempotency(status, updated_at)")

    def claim(self, session_id: str, client_message_id: str, request_hash: str) -> dict:
        key = str(client_message_id).strip()
        if not key:
            raise ValueError("CLIENT_MESSAGE_ID_REQUIRED")
        stamp = _now()
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(
                "SELECT request_hash,status,response_json FROM chat_request_idempotency WHERE session_id=? AND client_message_id=?",
                (session_id, key),
            ).fetchone()
            if row is None:
                con.execute(
                    "INSERT INTO chat_request_idempotency(session_id,client_message_id,request_hash,status,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                    (session_id, key, request_hash, "PROCESSING", stamp, stamp),
                )
                con.commit()
                return {"status": "CLAIMED"}
            if row["request_hash"] != request_hash:
                con.commit()
                return {"status": "ID_CONFLICT"}
            if row["status"] == "COMPLETED":
                response = json.loads(row["response_json"] or "{}")
                con.commit()
                return {"status": "COMPLETED", "response": response}
            if row["status"] == "FAILED":
                con.execute(
                    "UPDATE chat_request_idempotency SET status='PROCESSING',updated_at=? WHERE session_id=? AND client_message_id=?",
                    (stamp, session_id, key),
                )
                con.commit()
                return {"status": "CLAIMED"}
            con.commit()
            return {"status": "IN_PROGRESS"}

    def complete(self, session_id: str, client_message_id: str, response: dict) -> None:
        stamp = _now()
        payload = json.dumps(response, ensure_ascii=False, sort_keys=True)
        with self.connect() as con:
            cur = con.execute(
                "UPDATE chat_request_idempotency SET status='COMPLETED',response_json=?,updated_at=? WHERE session_id=? AND client_message_id=? AND status='PROCESSING'",
                (payload, stamp, session_id, str(client_message_id).strip()),
            )
            if cur.rowcount != 1:
                raise RuntimeError("IDEMPOTENCY_COMPLETION_STATE_MISMATCH")

    def fail(self, session_id: str, client_message_id: str) -> None:
        with self.connect() as con:
            con.execute(
                "UPDATE chat_request_idempotency SET status='FAILED',updated_at=? WHERE session_id=? AND client_message_id=? AND status='PROCESSING'",
                (_now(), session_id, str(client_message_id).strip()),
            )
