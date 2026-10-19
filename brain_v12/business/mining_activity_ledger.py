"""Append-only record of mining work, separate from verified financial revenue.

Recording an activity never implies live mining, accepted shares, payout, or income.
The revenue ledger remains the only path for recognizing verified revenue.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

_ALLOWED_MODES = {"SIMULATION", "LIVE"}
_ALLOWED_TYPES = {
    "SHA256D_RESULT",
    "HASHRATE_MEASUREMENT",
    "SIMULATOR_RUN",
    "ACCEPTED_SHARES",
    "MINING_ACTIVITY",
}


class MiningActivityLedger:
    """Persist activity observations and estimates without requiring payout proof."""

    def __init__(self, path: str | Path = "brain6_artifacts/mining/mining_activity.db"):
        raw = str(path)
        self._uri = raw == ":memory:"
        self.path = raw if self._uri else str(Path(raw).expanduser())
        if not self._uri:
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(
            self.path, timeout=30, isolation_level=None, check_same_thread=False,
            uri=self._uri,
        )
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA busy_timeout=30000")
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS mining_activity (
                activity_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                mode TEXT NOT NULL,
                activity_type TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                source TEXT NOT NULL,
                evidence_ref TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                estimated_amount TEXT,
                estimated_currency TEXT,
                activity_status TEXT NOT NULL,
                income_status TEXT NOT NULL
            )
            """
        )

    def close(self) -> None:
        self._db.close()

    @staticmethod
    def _snapshot(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "activity_id": row["activity_id"],
            "run_id": row["run_id"],
            "mode": row["mode"],
            "activity_type": row["activity_type"],
            "observed_at": row["observed_at"],
            "source": row["source"],
            "evidence_ref": row["evidence_ref"],
            "payload": json.loads(row["payload_json"]),
            "estimated_amount": row["estimated_amount"],
            "estimated_currency": row["estimated_currency"],
            "activity_status": row["activity_status"],
            "income_status": row["income_status"],
            "counts_as_verified_revenue": False,
        }

    def record(
        self,
        *,
        activity_id: str,
        run_id: str,
        mode: str,
        activity_type: str,
        payload: dict[str, Any],
        observed_at: str | None = None,
        source: str = "",
        evidence_ref: str = "",
        estimated_amount: str | int | float | None = None,
        estimated_currency: str | None = None,
    ) -> dict[str, Any]:
        """Record an activity even when payout evidence is absent.

        SIMULATION records remain explicitly simulation-only. Estimates are
        stored separately and can never change verified revenue balances.
        """
        activity_id = str(activity_id).strip()
        run_id = str(run_id).strip()
        mode = str(mode).strip().upper()
        activity_type = str(activity_type).strip().upper()
        if not activity_id or not run_id:
            raise ValueError("activity_id and run_id are required")
        if mode not in _ALLOWED_MODES:
            raise ValueError("mode must be SIMULATION or LIVE")
        if activity_type not in _ALLOWED_TYPES:
            raise ValueError("unsupported activity_type")
        if not isinstance(payload, dict):
            raise ValueError("payload must be a structured object")

        timestamp_was_supplied = observed_at is not None
        timestamp = str(observed_at or datetime.now(timezone.utc).isoformat()).strip()
        if not timestamp:
            raise ValueError("observed_at must not be empty")

        amount_text = None
        currency_text = str(estimated_currency or "").strip().upper() or None
        if estimated_amount is not None:
            try:
                amount = Decimal(str(estimated_amount))
            except (InvalidOperation, ValueError):
                raise ValueError("estimated_amount must be a finite non-negative number")
            if not amount.is_finite() or amount < 0:
                raise ValueError("estimated_amount must be a finite non-negative number")
            if not currency_text:
                raise ValueError("estimated_currency is required with estimated_amount")
            amount_text = format(amount, "f")
        elif currency_text:
            raise ValueError("estimated_amount is required with estimated_currency")

        activity_status = (
            "SIMULATION_RECORDED" if mode == "SIMULATION"
            else ("LIVE_ACTIVITY_UNVERIFIED" if source.strip() else "SOURCE_MISSING")
        )
        income_status = "ESTIMATE_ONLY" if amount_text is not None else "NO_REVENUE_CLAIM"
        payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        values = (
            activity_id, run_id, mode, activity_type, timestamp,
            str(source).strip(), str(evidence_ref).strip(), payload_json,
            amount_text, currency_text, activity_status, income_status,
        )

        self._db.execute("BEGIN IMMEDIATE")
        try:
            existing = self._db.execute(
                "SELECT * FROM mining_activity WHERE activity_id=?", (activity_id,)
            ).fetchone()
            if existing is not None:
                snapshot = self._snapshot(existing)
                requested = {
                    "activity_id": activity_id, "run_id": run_id, "mode": mode,
                    "activity_type": activity_type,
                    "observed_at": timestamp if timestamp_was_supplied else snapshot["observed_at"],
                    "source": str(source).strip(), "evidence_ref": str(evidence_ref).strip(),
                    "payload": json.loads(payload_json), "estimated_amount": amount_text,
                    "estimated_currency": currency_text, "activity_status": activity_status,
                    "income_status": income_status, "counts_as_verified_revenue": False,
                }
                if snapshot != requested:
                    raise ValueError("conflicting activity_id already exists")
                self._db.execute("COMMIT")
                return snapshot

            self._db.execute(
                """
                INSERT INTO mining_activity (
                    activity_id, run_id, mode, activity_type, observed_at,
                    source, evidence_ref, payload_json, estimated_amount,
                    estimated_currency, activity_status, income_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            row = self._db.execute(
                "SELECT * FROM mining_activity WHERE activity_id=?", (activity_id,)
            ).fetchone()
            self._db.execute("COMMIT")
            return self._snapshot(row)
        except Exception:
            if self._db.in_transaction:
                self._db.execute("ROLLBACK")
            raise

    def get(self, activity_id: str) -> dict[str, Any] | None:
        row = self._db.execute(
            "SELECT * FROM mining_activity WHERE activity_id=?", (str(activity_id),)
        ).fetchone()
        return self._snapshot(row) if row is not None else None

    def list_for_run(self, run_id: str) -> list[dict[str, Any]]:
        rows = self._db.execute(
            "SELECT * FROM mining_activity WHERE run_id=? ORDER BY observed_at, activity_id",
            (str(run_id),),
        ).fetchall()
        return [self._snapshot(row) for row in rows]
