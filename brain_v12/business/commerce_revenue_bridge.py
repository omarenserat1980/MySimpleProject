"""Durable, retryable bridge from verified commerce orders to the revenue ledger.

This bridge never moves money. It recognizes ledger revenue only after the
persisted commerce order carries independently verified payment authority and
delivery/reconciliation evidence. Pending outbox entries are safe to retry.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from contextlib import contextmanager

from .revenue_ledger_store import RevenueLedgerStore


class CommerceRevenueBridge:
    def __init__(self, outbox_path: str, commerce_store, ledger: RevenueLedgerStore):
        self.path = str(outbox_path)
        Path(self.path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self.commerce_store = commerce_store
        self.ledger = ledger
        with self._db() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS commerce_revenue_outbox (
                event_key TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                payment_transaction_id TEXT NOT NULL,
                delivery_evidence_ref TEXT NOT NULL,
                reconciliation_ref TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                last_error TEXT,
                attempts INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=30000")
        db.execute("PRAGMA journal_mode=WAL")
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _event_key(order_id: str, transaction_id: str) -> str:
        return f"commerce-revenue-v1:{order_id}:{transaction_id}"

    def enqueue(self, order_id: str, payment_transaction_id: str,
                delivery_evidence_ref: str, reconciliation_ref: str) -> dict:
        values = tuple(str(v).strip() for v in (
            order_id, payment_transaction_id, delivery_evidence_ref, reconciliation_ref
        ))
        if not all(values):
            raise ValueError("order, transaction, delivery, and reconciliation references are required")
        order_id, transaction_id, delivery_ref, reconciliation = values
        key = self._event_key(order_id, transaction_id)
        with self._db() as db:
            row = db.execute("SELECT * FROM commerce_revenue_outbox WHERE event_key=?", (key,)).fetchone()
            if row:
                expected = (row["delivery_evidence_ref"], row["reconciliation_ref"])
                if expected != (delivery_ref, reconciliation):
                    raise ValueError("conflicting realization request for existing commerce event")
                return dict(row)
            db.execute("""INSERT INTO commerce_revenue_outbox
                (event_key, order_id, payment_transaction_id, delivery_evidence_ref, reconciliation_ref)
                VALUES (?, ?, ?, ?, ?)""",
                (key, order_id, transaction_id, delivery_ref, reconciliation))
            return dict(db.execute("SELECT * FROM commerce_revenue_outbox WHERE event_key=?", (key,)).fetchone())

    def get(self, order_id: str, payment_transaction_id: str) -> dict | None:
        with self._db() as db:
            row = db.execute("SELECT * FROM commerce_revenue_outbox WHERE event_key=?",
                             (self._event_key(order_id, payment_transaction_id),)).fetchone()
            return dict(row) if row else None

    def cancel_if_uncommitted(self, order_id: str, payment_transaction_id: str) -> None:
        """Cancel a pre-enqueued event only when commerce transition failed."""
        with self._db() as db:
            db.execute("UPDATE commerce_revenue_outbox SET status='CANCELLED', last_error='commerce transition rejected', updated_at=CURRENT_TIMESTAMP WHERE event_key=? AND status='PENDING'",
                       (self._event_key(order_id, payment_transaction_id),))

    def pending(self, limit: int = 100) -> list[dict]:
        limit = max(1, min(int(limit), 500))
        with self._db() as db:
            rows = db.execute("SELECT * FROM commerce_revenue_outbox WHERE status='PENDING' ORDER BY updated_at LIMIT ?", (limit,)).fetchall()
            return [dict(row) for row in rows]

    def reconcile_pending(self, limit: int = 100) -> dict:
        results = []
        for event in self.pending(limit):
            try:
                result = self.reconcile(event["order_id"], event["payment_transaction_id"])
                results.append({"order_id": event["order_id"], "status": result["status"]})
            except Exception as exc:
                results.append({"order_id": event["order_id"], "status": "PENDING", "reason": str(exc)[:300]})
        return {"processed": len(results), "completed": sum(x["status"] == "COMPLETED" for x in results), "results": results}

    def reconcile(self, order_id: str, payment_transaction_id: str) -> dict:
        key = self._event_key(order_id, payment_transaction_id)
        with self._db() as db:
            row = db.execute("SELECT * FROM commerce_revenue_outbox WHERE event_key=?", (key,)).fetchone()
            if row is None:
                raise ValueError("outbox event not found")
            event = dict(row)
            if event["status"] == "COMPLETED":
                return {"status": "COMPLETED", "ledger": self.ledger.get(order_id), "attempts": event["attempts"]}
            db.execute("UPDATE commerce_revenue_outbox SET attempts=attempts+1, last_error=NULL, updated_at=CURRENT_TIMESTAMP WHERE event_key=?", (key,))

        try:
            order = self.commerce_store.get(order_id)
            if not order:
                raise ValueError("commerce order not found; event remains pending")
            if order.get("state") != "REVENUE_REALIZED":
                raise ValueError("commerce order is not durably REVENUE_REALIZED; event remains pending")
            payment = order.get("payment", {})
            delivery = order.get("delivery", {})
            authority = order.get("revenue_authority", {})
            if payment.get("status") != "VERIFIED" or delivery.get("status") != "DELIVERED":
                raise ValueError("verified payment and delivery are required")
            if authority.get("status") != "INDEPENDENTLY_VERIFIED":
                raise ValueError("independent payment authority is required")
            if authority.get("order_id") != order_id:
                raise ValueError("revenue authority order mismatch")
            if authority.get("payment_transaction_id") != payment_transaction_id or payment.get("transaction_id") != payment_transaction_id:
                raise ValueError("revenue authority transaction mismatch")
            if not authority.get("provider") or not authority.get("event_id") or not authority.get("evidence_ref"):
                raise ValueError("complete provider authority evidence is required")
            if order.get("revenue", {}).get("status") != "REALIZED":
                raise ValueError("commerce realization evidence missing")
            if order["revenue"].get("delivery_evidence_ref") != event["delivery_evidence_ref"] or order["revenue"].get("reconciliation_ref") != event["reconciliation_ref"]:
                raise ValueError("outbox evidence does not match persisted commerce realization")

            amount = str(order.get("product", {}).get("price_usd", "")).strip()
            if not amount:
                raise ValueError("order amount missing")
            self.ledger.create(order_id, amount, "USD")
            self.ledger.verify(order_id, {
                "transaction_id": payment_transaction_id,
                "evidence_ref": authority["evidence_ref"],
                "source": authority["provider"],
                "verification_status": "INDEPENDENTLY_VERIFIED",
                "amount": amount,
                "currency": "USD",
            })
            ledger_snapshot = self.ledger.realize(order_id, {
                "delivery_evidence_ref": event["delivery_evidence_ref"],
                "reconciliation_ref": event["reconciliation_ref"],
            })
            with self._db() as db:
                db.execute("UPDATE commerce_revenue_outbox SET status='COMPLETED', last_error=NULL, updated_at=CURRENT_TIMESTAMP WHERE event_key=?", (key,))
            return {"status": "COMPLETED", "ledger": ledger_snapshot, "attempts": event["attempts"] + 1}
        except Exception as exc:
            # Persist a bounded diagnostic; never claim realization if any step failed.
            with self._db() as db:
                db.execute("UPDATE commerce_revenue_outbox SET status='PENDING', last_error=?, updated_at=CURRENT_TIMESTAMP WHERE event_key=?",
                           (str(exc)[:500], key))
            raise
