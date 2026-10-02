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
            s.transition(oid, "PAYMENT_VERIFIED", "provider-receipt:smoke")
            s.transition(oid, "DELIVERY_PENDING", "delivery-request:smoke")
            s.transition(oid, "DELIVERED", "delivery-proof:smoke")
            final = s.transition(oid, "REVENUE_REALIZED", "reconciliation:smoke")
            self.assertEqual(final["state"], "REVENUE_REALIZED")

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


if __name__ == "__main__":
    unittest.main()
