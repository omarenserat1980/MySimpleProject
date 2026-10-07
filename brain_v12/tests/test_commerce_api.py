import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.commerce_api import CommerceOrderIn, CommerceStore


class CommerceApiTests(unittest.TestCase):
    def test_order_lifecycle_requires_payment_and_delivery_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            s = CommerceStore(str(Path(d) / "commerce.json"))
            order = s.create(CommerceOrderIn(
                customer_name="Test Customer",
                contact="test@example.com",
                product_id="ai-starter-kit",
                details="smoke",
            ))
            oid = order["order_id"]
            s.transition(oid, "PAYMENT_PENDING", "checkout-intent:smoke")
            s.transition(oid, "PAYMENT_VERIFIED", {"transaction_id": "tx-smoke", "evidence_ref": "provider-receipt:smoke"})
            s.transition(oid, "DELIVERY_PENDING", "delivery-request:smoke")
            s.transition(oid, "DELIVERED", "delivery-proof:smoke")
            with self.assertRaises(Exception):
                s.transition(oid, "REVENUE_REALIZED", {"delivery_evidence_ref": "delivery-proof:smoke", "reconciliation_ref": "reconciliation:smoke"})

            data = s._read()
            data[oid]["revenue_authority"] = {
                "status": "INDEPENDENTLY_VERIFIED",
                "order_id": oid,
                "payment_transaction_id": "tx-smoke",
                "evidence_ref": "authority-proof:smoke",
            }
            s._write(data)
            final = s.transition(oid, "REVENUE_REALIZED", {"delivery_evidence_ref": "delivery-proof:smoke", "reconciliation_ref": "reconciliation:smoke"})
            self.assertEqual(final["state"], "REVENUE_REALIZED")
            self.assertEqual(final["revenue"]["authority_ref"], "authority-proof:smoke")

    def test_revenue_cannot_be_realized_without_verified_payment(self):
        with tempfile.TemporaryDirectory() as d:
            s = CommerceStore(str(Path(d) / "commerce.json"))
            order = s.create(CommerceOrderIn(
                customer_name="Test Customer",
                contact="test@example.com",
                product_id="media-toolkit",
            ))
            oid = order["order_id"]
            s.transition(oid, "PAYMENT_PENDING", "checkout-intent:smoke")
            with self.assertRaises(Exception):
                s.transition(oid, "PAYMENT_VERIFIED", "")
            self.assertEqual(s.get(oid)["state"], "PAYMENT_PENDING")

    def test_free_form_payment_and_revenue_evidence_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            s = CommerceStore(str(Path(d) / "commerce.json"))
            order = s.create(CommerceOrderIn(customer_name="Test", contact="test@example.com", product_id="ai-starter-kit"))
            oid = order["order_id"]
            s.transition(oid, "PAYMENT_PENDING", "checkout-intent:smoke")
            with self.assertRaises(Exception):
                s.transition(oid, "PAYMENT_VERIFIED", "free-form-payment-proof")
            s.transition(oid, "PAYMENT_VERIFIED", {"transaction_id": "tx-1", "evidence_ref": "payment-proof:1"})
            s.transition(oid, "DELIVERY_PENDING", "delivery-request:1")
            s.transition(oid, "DELIVERED", "delivery-proof:1")
            with self.assertRaises(Exception):
                s.transition(oid, "REVENUE_REALIZED", "free-form-reconciliation")



if __name__ == "__main__":
    unittest.main()
