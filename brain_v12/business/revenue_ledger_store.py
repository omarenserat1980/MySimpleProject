"""SQLite-backed durable revenue ledger store.

The store persists state transitions atomically across process restarts. It does not
verify external payment or blockchain claims itself; callers must provide evidence
that passes RevenueRecord's existing evidence gates.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .revenue_ledger import RevenueRecord


class RevenueLedgerStore:
    """Durable, transactionally updated storage for RevenueRecord instances."""

    def __init__(self, path="brain6_artifacts/revenue/revenue_ledger.db"):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
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
        db = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=30000")
        if self.path != ":memory:":
            db.execute("PRAGMA journal_mode=WAL")
        return db

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
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM revenue_records WHERE opportunity_id=?",
                (opportunity_id,),
            ).fetchone()
            if row is not None:
                record = self._record(row)
                if record.amount_note != str(amount_note) or record.currency.upper() != str(currency).upper():
                    db.rollback()
                    raise ValueError("conflicting revenue record for opportunity_id")
                db.commit()
                return record.snapshot()
            record = RevenueRecord(str(opportunity_id), str(amount_note), str(currency))
            db.execute(
                """
                INSERT INTO revenue_records
                    (opportunity_id, amount_note, currency, evidence_json, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (record.opportunity_id, record.amount_note, record.currency, "[]", record.status),
            )
            db.commit()
            return record.snapshot()

    def get(self, opportunity_id):
        with self._connect() as db:
            return self._record(
                db.execute(
                    "SELECT * FROM revenue_records WHERE opportunity_id=?",
                    (opportunity_id,),
                ).fetchone()
            ).snapshot() if db.execute(
                "SELECT 1 FROM revenue_records WHERE opportunity_id=?",
                (opportunity_id,),
            ).fetchone() else None

    def _transition(self, opportunity_id, operation, evidence):
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM revenue_records WHERE opportunity_id=?",
                (opportunity_id,),
            ).fetchone()
            if row is None:
                db.rollback()
                raise ValueError("revenue record not found")
            record = self._record(row)
            result = operation(record, evidence)
            self._write(db, record)
            db.commit()
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
