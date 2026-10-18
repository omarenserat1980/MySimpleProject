"""Local SQLite contract tests for the Brain settlement gate.

These tests exercise conditional ledger SQL only. They do not connect to Cloudflare,
PayTabs, a bank, or production data and are not evidence of an actual settlement.
"""
import sqlite3
import unittest


class SettlementGateTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        CREATE TABLE orders (
            order_id TEXT PRIMARY KEY,
            state TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT NOT NULL
        );
        CREATE TABLE deliveries (
            delivery_id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            state TEXT NOT NULL
        );
        CREATE TABLE revenue_ledger (
            revenue_id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            tran_ref TEXT NOT NULL UNIQUE,
            amount REAL NOT NULL,
            currency TEXT NOT NULL,
            environment TEXT NOT NULL,
            state TEXT NOT NULL,
            settlement_reference TEXT UNIQUE,
            evidence TEXT NOT NULL DEFAULT '{}'
        );
        INSERT INTO orders VALUES ('O-LIVE', 'READY', 12.50, 'JOD');
        INSERT INTO deliveries VALUES ('D-LIVE', 'O-LIVE', 'READY');
        INSERT INTO revenue_ledger
          (revenue_id, order_id, tran_ref, amount, currency, environment, state)
          VALUES ('R-LIVE', 'O-LIVE', 'T-LIVE', 12.50, 'JOD', 'live',
                  'PAYMENT_VERIFIED_PENDING_DELIVERY');
        INSERT INTO orders VALUES ('O-TEST', 'READY', 5.00, 'JOD');
        INSERT INTO deliveries VALUES ('D-TEST', 'O-TEST', 'READY');
        INSERT INTO revenue_ledger
          (revenue_id, order_id, tran_ref, amount, currency, environment, state)
          VALUES ('R-TEST', 'O-TEST', 'T-TEST', 5.00, 'JOD', 'test',
                  'SANDBOX_PAYMENT_VERIFIED_PENDING_DELIVERY');
        """)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_delivery_only_moves_live_revenue_to_pending_settlement(self):
        self.db.execute("""
            UPDATE deliveries SET state = 'DELIVERED'
            WHERE delivery_id = ? AND state = 'READY'
        """, ("D-LIVE",))
        self.db.execute("""
            UPDATE orders SET state = 'COMPLETED'
            WHERE order_id = ? AND state = 'READY'
        """, ("O-LIVE",))
        result = self.db.execute("""
            UPDATE revenue_ledger
            SET state = 'DELIVERY_CONFIRMED_PENDING_SETTLEMENT'
            WHERE order_id = ? AND tran_ref = ?
              AND state = 'PAYMENT_VERIFIED_PENDING_DELIVERY'
              AND environment = 'live' AND amount = ? AND currency = ?
        """, ("O-LIVE", "T-LIVE", 12.50, "JOD"))
        self.assertEqual(result.rowcount, 1)
        state = self.db.execute(
            "SELECT state FROM revenue_ledger WHERE revenue_id = 'R-LIVE'"
        ).fetchone()["state"]
        self.assertEqual(state, "DELIVERY_CONFIRMED_PENDING_SETTLEMENT")
        self.assertNotEqual(state, "REVENUE_REALIZED")

    def test_sandbox_delivery_never_becomes_realized_revenue(self):
        result = self.db.execute("""
            UPDATE revenue_ledger
            SET state = 'DELIVERY_CONFIRMED_PENDING_SETTLEMENT'
            WHERE order_id = ? AND state = 'PAYMENT_VERIFIED_PENDING_DELIVERY'
              AND environment = 'live'
        """, ("O-TEST",))
        self.assertEqual(result.rowcount, 0)
        state = self.db.execute(
            "SELECT state FROM revenue_ledger WHERE revenue_id = 'R-TEST'"
        ).fetchone()["state"]
        self.assertEqual(state, "SANDBOX_PAYMENT_VERIFIED_PENDING_DELIVERY")

    def test_valid_settlement_gate_realizes_exactly_one_matching_live_row(self):
        result = self.db.execute("""
            UPDATE revenue_ledger
            SET state = 'REVENUE_REALIZED', settlement_reference = ?
            WHERE tran_ref = ? AND environment = 'live'
              AND state = 'DELIVERY_CONFIRMED_PENDING_SETTLEMENT'
              AND amount = ? AND currency = ?
              AND settlement_reference IS NULL
        """, ("SETTLE-001", "T-LIVE", 12.50, "JOD"))
        self.assertEqual(result.rowcount, 0, "must not realize before delivery is confirmed")
        self.db.execute("""
            UPDATE revenue_ledger
            SET state = 'DELIVERY_CONFIRMED_PENDING_SETTLEMENT'
            WHERE tran_ref = ? AND environment = 'live'
              AND state = 'PAYMENT_VERIFIED_PENDING_DELIVERY'
        """, ("T-LIVE",))
        result = self.db.execute("""
            UPDATE revenue_ledger
            SET state = 'REVENUE_REALIZED', settlement_reference = ?
            WHERE tran_ref = ? AND environment = 'live'
              AND state = 'DELIVERY_CONFIRMED_PENDING_SETTLEMENT'
              AND amount = ? AND currency = ?
              AND settlement_reference IS NULL
        """, ("SETTLE-001", "T-LIVE", 12.50, "JOD"))
        self.assertEqual(result.rowcount, 1)
        replay = self.db.execute("""
            UPDATE revenue_ledger
            SET state = 'REVENUE_REALIZED', settlement_reference = ?
            WHERE tran_ref = ? AND environment = 'live'
              AND state = 'DELIVERY_CONFIRMED_PENDING_SETTLEMENT'
              AND amount = ? AND currency = ?
              AND settlement_reference IS NULL
        """, ("SETTLE-001", "T-LIVE", 12.50, "JOD"))
        self.assertEqual(replay.rowcount, 0)

    def test_wrong_amount_or_currency_cannot_realize_revenue(self):
        self.db.execute("""
            UPDATE revenue_ledger SET state = 'DELIVERY_CONFIRMED_PENDING_SETTLEMENT'
            WHERE tran_ref = 'T-LIVE'
        """)
        for amount, currency in ((12.51, "JOD"), (12.50, "USD")):
            result = self.db.execute("""
                UPDATE revenue_ledger
                SET state = 'REVENUE_REALIZED', settlement_reference = ?
                WHERE tran_ref = ? AND environment = 'live'
                  AND state = 'DELIVERY_CONFIRMED_PENDING_SETTLEMENT'
                  AND amount = ? AND currency = ?
                  AND settlement_reference IS NULL
            """, (f"BAD-{amount}-{currency}", "T-LIVE", amount, currency))
            self.assertEqual(result.rowcount, 0)
        state = self.db.execute(
            "SELECT state FROM revenue_ledger WHERE tran_ref = 'T-LIVE'"
        ).fetchone()["state"]
        self.assertEqual(state, "DELIVERY_CONFIRMED_PENDING_SETTLEMENT")

    def test_settlement_reference_cannot_be_reused(self):
        self.db.execute("""
            UPDATE revenue_ledger SET state = 'DELIVERY_CONFIRMED_PENDING_SETTLEMENT'
            WHERE tran_ref = 'T-LIVE'
        """)
        self.db.execute("""
            UPDATE revenue_ledger SET state = 'REVENUE_REALIZED', settlement_reference = 'SETTLE-UNIQUE'
            WHERE tran_ref = 'T-LIVE' AND environment = 'live'
              AND state = 'DELIVERY_CONFIRMED_PENDING_SETTLEMENT'
              AND settlement_reference IS NULL
        """)
        self.db.execute("""
            INSERT INTO revenue_ledger
              (revenue_id, order_id, tran_ref, amount, currency, environment, state)
              VALUES ('R-OTHER', 'O-OTHER', 'T-OTHER', 12.50, 'JOD', 'live',
                      'DELIVERY_CONFIRMED_PENDING_SETTLEMENT')
        """)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("""
                UPDATE revenue_ledger SET state = 'REVENUE_REALIZED',
                    settlement_reference = 'SETTLE-UNIQUE'
                WHERE tran_ref = 'T-OTHER'
            """)


if __name__ == "__main__":
    unittest.main(verbosity=2)
