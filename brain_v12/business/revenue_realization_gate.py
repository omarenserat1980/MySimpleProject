"""Fail-closed revenue realization gate with a durable SQLite ledger.

This module records realized revenue only when production execution, delivery,
independent payment verification, and exact task/opportunity/order linkage agree.
It does not contact payment providers or claim that evidence is genuine by itself:
the caller must supply evidence produced by trusted worker/provider verifiers.
"""
from __future__ import annotations

import json
import sqlite3
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


class RevenueGateError(ValueError):
    """Evidence is missing, inconsistent, simulated, or already consumed."""


def _required(data: dict[str, Any], key: str) -> str:
    value = str(data.get(key, "")).strip()
    if not value:
        raise RevenueGateError(f"MISSING_{key.upper()}")
    return value


def _money(value: Any) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise RevenueGateError("INVALID_AMOUNT") from None
    if not amount.is_finite() or amount <= 0:
        raise RevenueGateError("INVALID_AMOUNT")
    return amount.quantize(Decimal("0.01"))


class RevenueRealizationGate:
    """SQLite-backed exactly-once ledger. Costs are recorded in a separate table."""

    def __init__(self, database: str | Path):
        self.database = str(database)
        with self._connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS realized_revenue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    provider_transaction_id TEXT NOT NULL UNIQUE,
                    task_id TEXT NOT NULL,
                    opportunity_id TEXT NOT NULL,
                    order_id TEXT NOT NULL,
                    worker_execution_id TEXT NOT NULL,
                    amount TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    payment_evidence_ref TEXT NOT NULL,
                    delivery_evidence_ref TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS operating_costs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    task_id TEXT NOT NULL,
                    opportunity_id TEXT NOT NULL,
                    amount TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    evidence_ref TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.database, timeout=10, isolation_level="IMMEDIATE")
        db.row_factory = sqlite3.Row
        return db

    def realize(self, *, task: dict[str, Any], worker: dict[str, Any],
                delivery: dict[str, Any], payment: dict[str, Any],
                idempotency_key: str) -> dict[str, Any]:
        """Validate all evidence, then atomically create one revenue entry."""
        key = str(idempotency_key).strip()
        if not key:
            raise RevenueGateError("IDEMPOTENCY_KEY_REQUIRED")

        task_id = _required(task, "task_id")
        opportunity_id = _required(task, "opportunity_id")
        order_id = _required(task, "order_id")

        # Explicit simulation/demo/test evidence can never become realized revenue.
        for label, evidence in (("task", task), ("worker", worker),
                                ("delivery", delivery), ("payment", payment)):
            mode = str(evidence.get("mode", "production")).lower()
            if mode in {"simulation", "simulated", "demo", "test", "fixture", "mock"}:
                raise RevenueGateError(f"SIMULATED_{label.upper()}_REJECTED")

        if str(worker.get("status", "")).upper() != "COMPLETED":
            raise RevenueGateError("WORKER_EXECUTION_NOT_COMPLETED")
        if str(worker.get("execution_kind", "")).lower() != "real":
            raise RevenueGateError("REAL_WORKER_EXECUTION_REQUIRED")
        execution_id = _required(worker, "execution_id")
        if _required(worker, "task_id") != task_id:
            raise RevenueGateError("WORKER_TASK_MISMATCH")
        if _required(worker, "opportunity_id") != opportunity_id:
            raise RevenueGateError("WORKER_OPPORTUNITY_MISMATCH")
        _required(worker, "evidence_ref")

        if str(delivery.get("status", "")).upper() != "ACCEPTED":
            raise RevenueGateError("DELIVERY_NOT_ACCEPTED")
        if _required(delivery, "task_id") != task_id:
            raise RevenueGateError("DELIVERY_TASK_MISMATCH")
        if _required(delivery, "opportunity_id") != opportunity_id:
            raise RevenueGateError("DELIVERY_OPPORTUNITY_MISMATCH")
        if _required(delivery, "execution_id") != execution_id:
            raise RevenueGateError("DELIVERY_EXECUTION_MISMATCH")
        delivery_ref = _required(delivery, "evidence_ref")

        if str(payment.get("verification_status", "")).upper() != "INDEPENDENTLY_VERIFIED":
            raise RevenueGateError("INDEPENDENT_PAYMENT_PROOF_REQUIRED")
        if str(payment.get("settlement_status", "")).upper() not in {"SETTLED", "COMPLETED"}:
            raise RevenueGateError("PAYMENT_NOT_SETTLED")
        if _required(payment, "order_id") != order_id:
            raise RevenueGateError("PAYMENT_ORDER_MISMATCH")
        if _required(payment, "task_id") != task_id:
            raise RevenueGateError("PAYMENT_TASK_MISMATCH")
        if _required(payment, "opportunity_id") != opportunity_id:
            raise RevenueGateError("PAYMENT_OPPORTUNITY_MISMATCH")
        provider = _required(payment, "provider").lower()
        transaction_id = _required(payment, "transaction_id")
        payment_ref = _required(payment, "evidence_ref")
        currency = _required(payment, "currency").upper()
        expected_currency = _required(task, "currency").upper()
        if currency != expected_currency:
            raise RevenueGateError("PAYMENT_CURRENCY_MISMATCH")
        amount = _money(payment.get("amount"))
        expected_amount = _money(task.get("expected_amount"))
        if amount != expected_amount:
            raise RevenueGateError("PAYMENT_AMOUNT_MISMATCH")

        with self._connect() as db:
            prior = db.execute(
                "SELECT * FROM realized_revenue WHERE idempotency_key=? OR provider_transaction_id=?",
                (key, transaction_id),
            ).fetchone()
            if prior:
                if prior["idempotency_key"] == key and prior["provider_transaction_id"] == transaction_id:
                    return {"status": "REVENUE_REALIZED", "duplicate": True,
                            "ledger_id": prior["id"], "amount": prior["amount"],
                            "currency": prior["currency"]}
                raise RevenueGateError("DUPLICATE_REVENUE_KEY_OR_TRANSACTION")
            cursor = db.execute("""
                INSERT INTO realized_revenue
                (idempotency_key, provider_transaction_id, task_id, opportunity_id,
                 order_id, worker_execution_id, amount, currency, provider,
                 payment_evidence_ref, delivery_evidence_ref)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (key, transaction_id, task_id, opportunity_id, order_id,
                  execution_id, format(amount, ".2f"), currency, provider,
                  payment_ref, delivery_ref))
            return {"status": "REVENUE_REALIZED", "duplicate": False,
                    "ledger_id": cursor.lastrowid, "amount": format(amount, ".2f"),
                    "currency": currency}

    def record_cost(self, *, task_id: str, opportunity_id: str, amount: Any,
                    currency: str, evidence_ref: str, idempotency_key: str) -> dict[str, Any]:
        """Record a cost separately; this never changes gross realized revenue."""
        values = [task_id.strip(), opportunity_id.strip(), currency.strip().upper(),
                  evidence_ref.strip(), idempotency_key.strip()]
        if not all(values):
            raise RevenueGateError("COST_FIELDS_REQUIRED")
        cost = _money(amount)
        with self._connect() as db:
            try:
                cur = db.execute("""
                    INSERT INTO operating_costs
                    (idempotency_key, task_id, opportunity_id, amount, currency, evidence_ref)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (values[4], values[0], values[1], format(cost, ".2f"),
                      values[2], values[3]))
            except sqlite3.IntegrityError:
                row = db.execute("SELECT * FROM operating_costs WHERE idempotency_key=?",
                                 (values[4],)).fetchone()
                if row and row["task_id"] == values[0] and row["amount"] == format(cost, ".2f") and row["currency"] == values[2]:
                    return {"status": "COST_RECORDED", "duplicate": True, "cost_id": row["id"]}
                raise RevenueGateError("DUPLICATE_COST_KEY_CONFLICT") from None
            return {"status": "COST_RECORDED", "duplicate": False, "cost_id": cur.lastrowid}

    def summary(self) -> dict[str, Any]:
        """Return gross revenue and costs grouped by currency, never net them together."""
        with self._connect() as db:
            revenue = [dict(r) for r in db.execute(
                "SELECT currency, SUM(CAST(amount AS REAL)) AS amount, COUNT(*) AS entries "
                "FROM realized_revenue GROUP BY currency ORDER BY currency")]
            costs = [dict(r) for r in db.execute(
                "SELECT currency, SUM(CAST(amount AS REAL)) AS amount, COUNT(*) AS entries "
                "FROM operating_costs GROUP BY currency ORDER BY currency")]
        return {"status": "OK", "realized_revenue_gross": revenue, "operating_costs_separate": costs}
