"""SQLite-backed durable revenue ledger store.

This layer persists already-validated RevenueRecord transitions. It does not
verify payment providers, execute transactions, or turn simulations into revenue.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

from .revenue_ledger import RevenueRecord


class RevenueLedgerStore:
    """Durable, transactionally updated storage for revenue records."""

    def __init__(self, path="brain6_artifacts/revenue/revenue_ledger.db"):
        raw_path = str(path)
        self._uri = raw_path == ":memory:"
        self.path = raw_path if self._uri else str(Path(raw_path).expanduser())
        self._dsn = (
            f"file:brain-revenue-{uuid.uuid4().hex}?mode=memory&cache=shared"
            if self._uri else self.path
        )
        self._keeper = self._connect() if self._uri else None
        if not self._uri:
            Path(self.path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS revenue_records (
                    opportunity_id TEXT PRIMARY KEY,
                    amount_note TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def _connect(self):
        db = sqlite3.connect(
            self._dsn, timeout=30, isolation_level=None, uri=self._uri
        )
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=30000")
        if not self._uri:
            db.execute("PRAGMA journal_mode=WAL")
        return db

    @contextmanager
    def _connection(self):
        """Commit/rollback transaction scope and always close the connection."""
        db = self._connect()
        try:
            with db:
                yield db
        finally:
            db.close()

    def close(self):
        """Release the keeper connection used by an in-memory database."""
        if self._keeper is not None:
            self._keeper.close()
            self._keeper = None

    @staticmethod
    def _record(row):
        if row is None:
            return None
        return RevenueRecord(
            opportunity_id=row["opportunity_id"],
            amount_note=row["amount_note"],
            currency=row["currency"],
            evidence=json.loads(row["evidence_json"]),
            status=row["status"],
        )

    @staticmethod
    def _write(db, record):
        db.execute(
            """
            UPDATE revenue_records
               SET amount_note=?, currency=?, evidence_json=?, status=?,
                   updated_at=CURRENT_TIMESTAMP
             WHERE opportunity_id=?
            """,
            (
                record.amount_note,
                record.currency,
                json.dumps(record.evidence, ensure_ascii=False, separators=(",", ":")),
                record.status,
                record.opportunity_id,
            ),
        )

    def create(self, opportunity_id, amount_note, currency):
        """Create once; an exact retry returns the existing record."""
        opportunity_id = str(opportunity_id).strip()
        amount_note = str(amount_note).strip()
        currency = str(currency).strip()
        if not opportunity_id or not amount_note or not currency:
            raise ValueError("opportunity_id, amount_note, and currency are required")
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM revenue_records WHERE opportunity_id=?",
                (opportunity_id,),
            ).fetchone()
            if row is not None:
                record = self._record(row)
                if record.amount_note != amount_note or record.currency.upper() != currency.upper():
                    raise ValueError("conflicting revenue record for opportunity_id")
                return record.snapshot()
            record = RevenueRecord(opportunity_id, amount_note, currency)
            db.execute(
                """INSERT INTO revenue_records
                   (opportunity_id, amount_note, currency, evidence_json, status)
                   VALUES (?, ?, ?, ?, ?)""",
                (record.opportunity_id, record.amount_note, record.currency, "[]", record.status),
            )
            return record.snapshot()

    def get(self, opportunity_id):
        with self._connection() as db:
            row = db.execute(
                "SELECT * FROM revenue_records WHERE opportunity_id=?",
                (str(opportunity_id),),
            ).fetchone()
            record = self._record(row)
            return record.snapshot() if record is not None else None

    def _transition(self, opportunity_id, operation, evidence):
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM revenue_records WHERE opportunity_id=?",
                (str(opportunity_id),),
            ).fetchone()
            if row is None:
                raise ValueError("revenue record not found")
            record = self._record(row)
            result = operation(record, evidence)
            self._write(db, record)
            return result

    def verify(self, opportunity_id, evidence):
        return self._transition(opportunity_id, lambda record, item: record.verify(item), evidence)

    def realize(self, opportunity_id, evidence):
        return self._transition(opportunity_id, lambda record, item: record.realize(item), evidence)

    def realize_from_mining_verification(self, opportunity_id, verification):
        return self._transition(
            opportunity_id,
            lambda record, item: record.realize_from_mining_verification(item),
            verification,
        )
