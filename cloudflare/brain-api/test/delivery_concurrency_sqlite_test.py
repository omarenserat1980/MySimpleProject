"""SQLite regression for the D1 delivery-to-settlement gate.

This mirrors the conditional SQL in confirmDelivery. It is local-only and does
not connect to Cloudflare, PayTabs, or any production service. Delivery alone
must not realize revenue; settlement verification is a separate gate.
"""
import json
import sqlite3
import unittest


class DeliveryRevenueGateTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        CREATE TABLE orders(order_id TEXT PRIMARY KEY, state TEXT NOT NULL, amount REAL NOT NULL, currency TEXT NOT NULL);
        CREATE TABLE deliveries(delivery_id TEXT PRIMARY KEY, order_id TEXT NOT NULL, state TEXT NOT NULL, delivered_at TEXT);
        CREATE TABLE revenue_ledger(
            revenue_id TEXT PRIMARY KEY, order_id TEXT NOT NULL, tran_ref TEXT NOT NULL,
            amount REAL NOT NULL, currency TEXT NOT NULL, state TEXT NOT NULL,
            evidence TEXT NOT NULL, environment TEXT NOT NULL
        );
        INSERT INTO orders VALUES ('O-1', 'READY', 10.0, 'JOD');
        INSERT INTO deliveries VALUES ('D-1', 'O-1', 'READY', NULL);
        INSERT INTO revenue_ledger VALUES (
            'R-1', 'O-1', 'T-1', 10.0, 'JOD',
            'PAYMENT_VERIFIED_PENDING_DELIVERY', '{}', 'live'
        );
        """)
        self.delivery_update = """UPDATE deliveries SET state='DELIVERED', delivered_at=CURRENT_TIMESTAMP
            WHERE delivery_id=? AND state='READY'"""
        self.order_update = """UPDATE orders SET state='COMPLETED'
            WHERE order_id=? AND state='READY'"""
        self.revenue_update = """UPDATE revenue_ledger
            SET state='DELIVERY_CONFIRMED_PENDING_SETTLEMENT',
                evidence=json_patch(evidence, ?)
            WHERE order_id=? AND tran_ref=?
              AND state='PAYMENT_VERIFIED_PENDING_DELIVERY'
              AND environment='live' AND amount=? AND currency=?
              AND EXISTS (
                SELECT 1 FROM deliveries d JOIN orders o ON o.order_id=d.order_id
                WHERE d.delivery_id=? AND d.order_id=?
                  AND d.state='DELIVERED' AND o.state='COMPLETED'
              )"""

    def tearDown(self):
        self.db.close()

    def confirm(self):
        evidence = json.dumps({
            "delivery_id": "D-1",
            "delivery_state": "DELIVERED",
            "settlement_status": "NOT_YET_VERIFIED",
        })
        self.db.execute("BEGIN")
        results = [
            self.db.execute(self.delivery_update, ("D-1",)),
            self.db.execute(self.order_update, ("O-1",)),
            self.db.execute(self.revenue_update, (
                evidence, "O-1", "T-1", 10.0, "JOD", "D-1", "O-1"
            )),
        ]
        changes = [result.rowcount for result in results]
        self.db.commit()
        return changes

    def test_delivery_advances_only_to_pending_settlement(self):
        self.assertEqual(self.confirm(), [1, 1, 1])
        state = self.db.execute("SELECT state FROM revenue_ledger").fetchone()[0]
        self.assertEqual(state, "DELIVERY_CONFIRMED_PENDING_SETTLEMENT")
        self.assertNotEqual(state, "REVENUE_REALIZED")

    def test_replay_does_not_advance_ledger_twice(self):
        self.assertEqual(self.confirm(), [1, 1, 1])
        self.assertEqual(self.confirm(), [0, 0, 0])
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM revenue_ledger").fetchone()[0], 1)
        self.assertEqual(
            self.db.execute("SELECT state FROM revenue_ledger").fetchone()[0],
            "DELIVERY_CONFIRMED_PENDING_SETTLEMENT",
        )

    def test_revenue_guard_rejects_uncompleted_order(self):
        self.db.execute("UPDATE deliveries SET state='DELIVERED' WHERE delivery_id='D-1'")
        self.db.execute("UPDATE orders SET state='READY' WHERE order_id='O-1'")
        changed = self.db.execute(self.revenue_update, (
            json.dumps({"delivery_id": "D-1"}), "O-1", "T-1",
            10.0, "JOD", "D-1", "O-1"
        )).rowcount
        self.assertEqual(changed, 0)
        self.assertEqual(
            self.db.execute("SELECT state FROM revenue_ledger").fetchone()[0],
            "PAYMENT_VERIFIED_PENDING_DELIVERY",
        )

    def test_sandbox_payment_cannot_advance_live_revenue_ledger(self):
        self.db.execute("UPDATE revenue_ledger SET environment='test'")
        self.assertEqual(self.confirm(), [1, 1, 0])
        self.assertEqual(
            self.db.execute("SELECT state FROM revenue_ledger").fetchone()[0],
            "PAYMENT_VERIFIED_PENDING_DELIVERY",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
