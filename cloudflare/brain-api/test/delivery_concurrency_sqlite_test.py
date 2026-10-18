"""SQLite integration regression for the D1 delivery/revenue state gates.

This exercises the same conditional SQL shape used by confirmDelivery. It is a
local database test only; it does not connect to Cloudflare or PayTabs.
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
        CREATE TABLE revenue_ledger(revenue_id TEXT PRIMARY KEY, order_id TEXT NOT NULL, tran_ref TEXT NOT NULL, amount REAL NOT NULL, currency TEXT NOT NULL, state TEXT NOT NULL, evidence TEXT NOT NULL);
        INSERT INTO orders VALUES ('O-1', 'READY', 10.0, 'JOD');
        INSERT INTO deliveries VALUES ('D-1', 'O-1', 'READY', NULL);
        INSERT INTO revenue_ledger VALUES ('R-1', 'O-1', 'T-1', 10.0, 'JOD', 'PAYMENT_VERIFIED_PENDING_DELIVERY', '{}');
        """)
        self.delivery_update = """UPDATE deliveries SET state='DELIVERED', delivered_at=CURRENT_TIMESTAMP
            WHERE delivery_id=? AND state='READY'"""
        self.order_update = """UPDATE orders SET state='COMPLETED'
            WHERE order_id=? AND state='READY'"""
        self.revenue_update = """UPDATE revenue_ledger SET state='REVENUE_REALIZED',
            evidence=json_patch(evidence, ?)
            WHERE order_id=? AND tran_ref=? AND state='PAYMENT_VERIFIED_PENDING_DELIVERY'
              AND amount=? AND currency=?
              AND EXISTS (SELECT 1 FROM deliveries d JOIN orders o ON o.order_id=d.order_id
                          WHERE d.delivery_id=? AND d.order_id=? AND d.state='DELIVERED'
                            AND o.state='COMPLETED')"""

    def tearDown(self):
        self.db.close()

    def confirm(self):
        evidence = json.dumps({"delivery_id": "D-1", "delivery_state": "DELIVERED"})
        self.db.execute("BEGIN")
        results = [
            self.db.execute(self.delivery_update, ("D-1",)),
            self.db.execute(self.order_update, ("O-1",)),
            self.db.execute(self.revenue_update, (evidence, "O-1", "T-1", 10.0, "JOD", "D-1", "O-1")),
        ]
        changes = [r.rowcount for r in results]
        self.db.commit()
        return changes

    def test_first_confirmation_realizes_revenue_once(self):
        self.assertEqual(self.confirm(), [1, 1, 1])
        self.assertEqual(self.db.execute("SELECT state FROM revenue_ledger").fetchone()[0], "REVENUE_REALIZED")

    def test_replay_changes_no_rows_and_does_not_create_second_revenue(self):
        self.assertEqual(self.confirm(), [1, 1, 1])
        self.assertEqual(self.confirm(), [0, 0, 0])
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM revenue_ledger").fetchone()[0], 1)
        self.assertEqual(self.db.execute("SELECT state FROM revenue_ledger").fetchone()[0], "REVENUE_REALIZED")

    def test_revenue_guard_rejects_uncompleted_order(self):
        self.db.execute("UPDATE deliveries SET state='DELIVERED' WHERE delivery_id='D-1'")
        self.db.execute("UPDATE orders SET state='READY' WHERE order_id='O-1'")
        changed = self.db.execute(self.revenue_update, (
            json.dumps({"delivery_id": "D-1"}), "O-1", "T-1", 10.0, "JOD", "D-1", "O-1"
        )).rowcount
        self.assertEqual(changed, 0)
        self.assertEqual(self.db.execute("SELECT state FROM revenue_ledger").fetchone()[0],
                         "PAYMENT_VERIFIED_PENDING_DELIVERY")


if __name__ == "__main__":
    unittest.main(verbosity=2)
