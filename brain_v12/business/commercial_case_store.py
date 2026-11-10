"""Durable SQLite storage for commercial opportunity cases.

Evidence references are metadata only; recording one never verifies a stage or revenue.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from brain_v12.business.commercial_case import CommercialCase


def _database_path() -> Path:
    configured = os.getenv("BRAIN_COMMERCIAL_CASES_DB")
    if configured:
        return Path(configured).expanduser()
    runtime_home = Path(os.getenv("BRAIN_RUNTIME_HOME", "~/.brain/runtime")).expanduser()
    return runtime_home / "commercial_cases.sqlite3"


class CommercialCaseStore:
    def __init__(self, path: str | os.PathLike[str] | None = None):
        self.path = Path(path).expanduser() if path else _database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=10000")
        return db

    def _initialize(self) -> None:
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS commercial_cases (
                    case_id TEXT PRIMARY KEY,
                    capability_id TEXT NOT NULL,
                    offer TEXT NOT NULL,
                    prospect_evidence TEXT,
                    customer_evidence TEXT,
                    delivery_evidence TEXT,
                    payment_evidence TEXT,
                    revenue_evidence TEXT,
                    cost_evidence TEXT,
                    evidence_refs_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                )
            """)

    @staticmethod
    def _from_row(row: sqlite3.Row) -> CommercialCase:
        return CommercialCase(
            case_id=row["case_id"],
            capability_id=row["capability_id"],
            offer=row["offer"],
            prospect_evidence=row["prospect_evidence"],
            customer_evidence=row["customer_evidence"],
            delivery_evidence=row["delivery_evidence"],
            payment_evidence=row["payment_evidence"],
            revenue_evidence=row["revenue_evidence"],
            cost_evidence=row["cost_evidence"],
            evidence_refs=json.loads(row["evidence_refs_json"]),
        )

    def list_cases(self) -> list[CommercialCase]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM commercial_cases ORDER BY created_at, case_id").fetchall()
        return [self._from_row(row) for row in rows]

    def get_case(self, case_id: str) -> CommercialCase | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM commercial_cases WHERE case_id=?", (case_id,)).fetchone()
        return self._from_row(row) if row else None

    def create_case(self, case: CommercialCase) -> None:
        record = case.to_record()
        try:
            with self._connect() as db:
                db.execute("""
                    INSERT INTO commercial_cases (
                        case_id, capability_id, offer, prospect_evidence, customer_evidence,
                        delivery_evidence, payment_evidence, revenue_evidence, cost_evidence,
                        evidence_refs_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    case.case_id, case.capability_id, case.offer, case.prospect_evidence,
                    case.customer_evidence, case.delivery_evidence, case.payment_evidence,
                    case.revenue_evidence, case.cost_evidence,
                    json.dumps(case.evidence_refs, ensure_ascii=False),
                ))
        except sqlite3.IntegrityError as exc:
            raise ValueError("CASE_EXISTS") from exc

    def add_evidence_reference(self, case_id: str, evidence_type: str, evidence_ref: str) -> CommercialCase | None:
        allowed = {"prospect", "customer", "delivery", "payment", "revenue", "cost", "other"}
        if evidence_type not in allowed:
            raise ValueError("INVALID_EVIDENCE_TYPE")
        ref = evidence_ref.strip()
        if not ref:
            raise ValueError("EVIDENCE_REFERENCE_REQUIRED")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM commercial_cases WHERE case_id=?", (case_id,)).fetchone()
            if row is None:
                db.rollback()
                return None
            refs: list[dict[str, Any]] = json.loads(row["evidence_refs_json"])
            candidate = {"type": evidence_type, "ref": ref, "verification_state": "UNVERIFIED"}
            if candidate not in refs:
                refs.append(candidate)
                db.execute(
                    "UPDATE commercial_cases SET evidence_refs_json=?, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE case_id=?",
                    (json.dumps(refs, ensure_ascii=False), case_id),
                )
            db.commit()
        return self.get_case(case_id)
