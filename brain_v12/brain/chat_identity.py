"""Self-hosted device credentials for Brain Chat.

Provision credentials only from a trusted local operator shell:
python -m brain_v12.brain.chat_identity issue --db brain_v12.db --account ACCOUNT --device-label DEVICE
The raw token is printed once; only its SHA-256 digest is persisted.
"""
from __future__ import annotations

import argparse
import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4


def _now():
    return datetime.now(timezone.utc)


def _stamp(value=None):
    return (value or _now()).isoformat()


class ChatIdentityStore:
    def __init__(self, path="brain_v12.db"):
        self.path = Path(path)

    def connect(self):
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        return con

    def init(self):
        with self.connect() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS chat_devices(
                    device_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    device_label TEXT NOT NULL,
                    token_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    revoked_at TEXT
                )
            """)
            con.execute("CREATE INDEX IF NOT EXISTS idx_chat_devices_account ON chat_devices(account_id)")
            con.commit()

    @staticmethod
    def _hash(token):
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def issue(self, account_id, device_label, ttl_days=90):
        account_id = str(account_id or "").strip()
        device_label = str(device_label or "").strip()
        if not account_id or not device_label:
            raise ValueError("account_id and device_label are required")
        if not 1 <= int(ttl_days) <= 365:
            raise ValueError("ttl_days must be between 1 and 365")
        token = secrets.token_urlsafe(32)
        device_id = str(uuid4())
        now = _now()
        with self.connect() as con:
            con.execute(
                "INSERT INTO chat_devices(device_id,account_id,device_label,token_hash,created_at,expires_at,revoked_at) "
                "VALUES(?,?,?,?,?,?,NULL)",
                (device_id, account_id, device_label, self._hash(token), _stamp(now),
                 _stamp(now + timedelta(days=int(ttl_days)))),
            )
            con.commit()
        return {"token": token, "device_id": device_id, "account_id": account_id}

    def authenticate(self, token):
        if not isinstance(token, str) or not token or len(token) > 512:
            return None
        with self.connect() as con:
            row = con.execute(
                "SELECT device_id,account_id,device_label,expires_at,revoked_at "
                "FROM chat_devices WHERE token_hash=?",
                (self._hash(token),),
            ).fetchone()
        if row is None or row["revoked_at"] is not None:
            return None
        if row["expires_at"]:
            try:
                if datetime.fromisoformat(row["expires_at"]) <= _now():
                    return None
            except ValueError:
                return None
        return {"device_id": row["device_id"], "account_id": row["account_id"],
                "device_label": row["device_label"]}

    def revoke(self, device_id):
        with self.connect() as con:
            cur = con.execute(
                "UPDATE chat_devices SET revoked_at=? WHERE device_id=? AND revoked_at IS NULL",
                (_stamp(), str(device_id)),
            )
            con.commit()
            return cur.rowcount == 1


def main():
    parser = argparse.ArgumentParser(description="Provision or revoke Brain Chat device credentials.")
    parser.add_argument("--db", default="brain_v12.db", help="Brain SQLite database path")
    sub = parser.add_subparsers(dest="action", required=True)
    issue = sub.add_parser("issue", help="issue a device token from a trusted local shell")
    issue.add_argument("--account", required=True, help="operator-assigned account identifier")
    issue.add_argument("--device-label", required=True, help="human-readable device label")
    issue.add_argument("--ttl-days", type=int, default=90)
    revoke = sub.add_parser("revoke", help="revoke a device credential")
    revoke.add_argument("--device-id", required=True)
    args = parser.parse_args()
    store = ChatIdentityStore(args.db)
    store.init()
    if args.action == "issue":
        result = store.issue(args.account, args.device_label, args.ttl_days)
        print("DEVICE_ID=" + result["device_id"])
        print("ACCOUNT_ID=" + result["account_id"])
        print("TOKEN=" + result["token"])
        print("Store this token securely; it cannot be retrieved again.")
    else:
        print("REVOKED=" + str(store.revoke(args.device_id)).lower())


if __name__ == "__main__":
    main()
