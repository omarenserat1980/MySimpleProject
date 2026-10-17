"""Explicit private-IP assignment registry for BRAIN-ASIC-001.

This stores an operator-supplied ASIC management IP in SQLite. It does not
configure a router/device, scan a network, contact the ASIC, start mining, or
mark connectivity/mining as verified. The address must already be assigned
or reserved on the user's local network.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = PROJECT_ROOT / ".brain" / "asic_identity.sqlite3"
DEFAULT_PRODUCT_ID = "BRAIN-ASIC-001"
DEFAULT_PORT = 4028


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_private_ipv4(value: str) -> str:
    try:
        address = ipaddress.ip_address(value.strip())
    except ValueError as exc:
        raise ValueError("ip must be a valid IPv4 address") from exc
    if address.version != 4 or not address.is_private or address.is_loopback or address.is_link_local:
        raise ValueError("ip must be a usable private IPv4 address on the local LAN")
    return str(address)


class ASICIPStore:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path or os.environ.get("BRAIN_ASIC_DB") or DEFAULT_DB).expanduser()

    def connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 10000")
        return conn

    def init(self) -> None:
        with self.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS asic_network_assignments (
                    product_id TEXT PRIMARY KEY,
                    ip_address TEXT NOT NULL,
                    api_port INTEGER NOT NULL CHECK(api_port BETWEEN 1 AND 65535),
                    transport TEXT NOT NULL DEFAULT 'tcp',
                    interface_name TEXT NOT NULL DEFAULT 'cgminer-compatible-api',
                    assignment_source TEXT NOT NULL,
                    connection_verified INTEGER NOT NULL DEFAULT 0 CHECK(connection_verified IN (0,1)),
                    live_mining_verified INTEGER NOT NULL DEFAULT 0 CHECK(live_mining_verified IN (0,1)),
                    notes TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL
                )
            """)

    def save(self, ip: str, port: int = DEFAULT_PORT, product_id: str = DEFAULT_PRODUCT_ID,
             source: str = "operator_supplied") -> dict:
        address = validate_private_ipv4(ip)
        if not 1 <= port <= 65535:
            raise ValueError("port must be between 1 and 65535")
        now = utc_now()
        note = ("Configured address only. Not a connectivity test, hardware identity proof, "
                "accepted-share proof, or live-mining proof.")
        with self.connect() as conn:
            conn.execute("""
                INSERT INTO asic_network_assignments (
                    product_id, ip_address, api_port, transport, interface_name,
                    assignment_source, connection_verified, live_mining_verified,
                    notes, created_at_utc, updated_at_utc
                ) VALUES (?, ?, ?, 'tcp', 'cgminer-compatible-api', ?, 0, 0, ?, ?, ?)
                ON CONFLICT(product_id) DO UPDATE SET
                    ip_address=excluded.ip_address,
                    api_port=excluded.api_port,
                    transport=excluded.transport,
                    interface_name=excluded.interface_name,
                    assignment_source=excluded.assignment_source,
                    connection_verified=0,
                    live_mining_verified=0,
                    notes=excluded.notes,
                    updated_at_utc=excluded.updated_at_utc
            """, (product_id, address, port, source, note, now, now))
        return self.get(product_id) or {}

    def get(self, product_id: str = DEFAULT_PRODUCT_ID) -> dict | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM asic_network_assignments WHERE product_id = ?", (product_id,)
            ).fetchone()
        return dict(row) if row else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Store a known ASIC-001 private LAN IP in SQLite")
    parser.add_argument("--db", type=Path, default=None)
    commands = parser.add_subparsers(dest="command", required=True)
    configure = commands.add_parser("configure", help="persist an already-assigned private IP")
    configure.add_argument("--ip", required=True, help="known ASIC management IPv4 on the local LAN")
    configure.add_argument("--port", type=int, default=DEFAULT_PORT)
    get = commands.add_parser("get", help="show the saved assignment")
    get.add_argument("--product-id", default=DEFAULT_PRODUCT_ID)
    args = parser.parse_args()
    store = ASICIPStore(args.db)
    store.init()
    try:
        result = store.save(args.ip, args.port) if args.command == "configure" else store.get(args.product_id)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
