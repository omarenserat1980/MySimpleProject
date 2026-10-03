"""SQLite-backed conversation sessions and per-session memory for Brain Chat."""

from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def _now():
    return datetime.now(timezone.utc).isoformat()


class ChatSessionStore:
    def __init__(self, path="brain_v12.db"):
        self.path = Path(path)

    def connect(self):
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        return con

    def init(self):
        with self.connect() as con:
            con.executescript("""
            CREATE TABLE IF NOT EXISTS chat_sessions(
              id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chat_session_messages(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id TEXT NOT NULL,
              role TEXT NOT NULL,
              content TEXT NOT NULL,
              metadata TEXT NOT NULL DEFAULT '{}',
              created_at TEXT NOT NULL,
              FOREIGN KEY(session_id) REFERENCES chat_sessions(id)
            );
            CREATE INDEX IF NOT EXISTS idx_chat_session_messages
              ON chat_session_messages(session_id, id);
            CREATE TABLE IF NOT EXISTS chat_session_memory(
              session_id TEXT PRIMARY KEY,
              summary TEXT NOT NULL DEFAULT '',
              updated_at TEXT NOT NULL,
              FOREIGN KEY(session_id) REFERENCES chat_sessions(id)
            );
            """)

    def create(self, title="New Brain Chat"):
        sid = str(uuid4())
        stamp = _now()
        with self.connect() as con:
            con.execute("INSERT INTO chat_sessions VALUES(?,?,?,?)",
                        (sid, title or "New Brain Chat", stamp, stamp))
            con.execute(
                "INSERT INTO chat_session_memory(session_id,summary,updated_at) VALUES(?,?,?)",
                (sid, "", stamp),
            )
            con.commit()
        return self.get(sid)

    def list(self):
        with self.connect() as con:
            rows = con.execute(
                "SELECT * FROM chat_sessions ORDER BY updated_at DESC"
            ).fetchall()
        return [dict(x) for x in rows]

    def get(self, session_id):
        with self.connect() as con:
            session = con.execute(
                "SELECT * FROM chat_sessions WHERE id=?", (session_id,)
            ).fetchone()
            if not session:
                return None
            messages = con.execute(
                "SELECT role,content,metadata,created_at FROM chat_session_messages "
                "WHERE session_id=? ORDER BY id", (session_id,)
            ).fetchall()
            memory = con.execute(
                "SELECT summary,updated_at FROM chat_session_memory WHERE session_id=?",
                (session_id,),
            ).fetchone()
        out = dict(session)
        out["messages"] = []
        for row in messages:
            item = dict(row)
            try:
                item["metadata"] = json.loads(item["metadata"])
            except Exception:
                item["metadata"] = {}
            out["messages"].append(item)
        out["memory"] = dict(memory) if memory else {"summary": "", "updated_at": None}
        return out

    def context_messages(self, session_id, limit=24):
        """Return recent conversation messages for model context."""
        limit = max(1, int(limit))
        with self.connect() as con:
            rows = con.execute(
                "SELECT role,content,metadata,created_at FROM chat_session_messages "
                "WHERE session_id=? ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        items = []
        for row in reversed(rows):
            item = dict(row)
            try:
                item["metadata"] = json.loads(item["metadata"])
            except Exception:
                item["metadata"] = {}
            items.append(item)
        return items

    def get_memory(self, session_id):
        with self.connect() as con:
            row = con.execute(
                "SELECT summary,updated_at FROM chat_session_memory WHERE session_id=?",
                (session_id,),
            ).fetchone()
        return dict(row) if row else None

    def set_memory(self, session_id, summary):
        stamp = _now()
        with self.connect() as con:
            exists = con.execute(
                "SELECT 1 FROM chat_sessions WHERE id=?", (session_id,)
            ).fetchone()
            if not exists:
                return None
            con.execute(
                "INSERT INTO chat_session_memory(session_id,summary,updated_at) VALUES(?,?,?) "
                "ON CONFLICT(session_id) DO UPDATE SET summary=excluded.summary,updated_at=excluded.updated_at",
                (session_id, str(summary or ""), stamp),
            )
            con.execute("UPDATE chat_sessions SET updated_at=? WHERE id=?",
                        (stamp, session_id))
            con.commit()
        return self.get_memory(session_id)

    def add_message(self, session_id, role, content, metadata=None):
        stamp = _now()
        with self.connect() as con:
            exists = con.execute(
                "SELECT 1 FROM chat_sessions WHERE id=?", (session_id,)
            ).fetchone()
            if not exists:
                return None
            con.execute(
                "INSERT INTO chat_session_messages(session_id,role,content,metadata,created_at) "
                "VALUES(?,?,?,?,?)",
                (session_id, role, content, json.dumps(metadata or {}, ensure_ascii=False), stamp),
            )
            con.execute("UPDATE chat_sessions SET updated_at=? WHERE id=?",
                        (stamp, session_id))
            con.commit()
        return self.get(session_id)
