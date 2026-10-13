import unittest

from brain.provider_hub.evidence import Evidence
from brain.provider_hub.paypal_commercial_flow import PayPalCommercialFlow


def capture():
    return {
        "id": "PP-ORDER-1",
        "status": "COMPLETED",
        "purchase_units": [{
            "reference_id": "EB-ORDER-1",
            "invoice_id": "EB-ORDER-1",
            "payments": {"captures": [{
                "id": "PP-CAPTURE-1",
                "status": "COMPLETED",
                "amount": {"value": "12.50", "currency_code": "USD"},
            }]},
        }],
    }


def delivery():
    return Evidence.create(
        evidence_id="delivery:EB-ORDER-1:1",
        evidence_type="DELIVERY_VERIFICATION",
        order_id="EB-ORDER-1",
        source="test-delivery",
        reference="delivery-proof-1",
        payload={"delivered": True, "artifact": "test-delivered-object"},
    )


def revenue():
    return Evidence.create(
        evidence_id="revenue:EB-ORDER-1:1",
        evidence_type="REVENUE_CONFIRMATION",
        order_id="EB-ORDER-1",
        source="test-ledger",
        reference="revenue-proof-1",
        payload={"accounting_confirmed": True},
    )


class PayPalCommercialFlowTests(unittest.TestCase):
    def setUp(self):
        self.flow = PayPalCommercialFlow()
        self.flow.register_order(
            order_id="EB-ORDER-1", paypal_order_id="PP-ORDER-1",
            amount_minor=1250, currency="USD", idempotency_key="intent-1",
        )

    def accept(self):
        return self.flow.accept_capture(
            response=capture(), order_id="EB-ORDER-1",
            paypal_order_id="PP-ORDER-1", amount="12.50", currency="USD",
        )

    def test_payment_stays_pending_until_delivery(self):
        result = self.accept()
        self.assertEqual(result.state, "PAYMENT_VERIFIED")
        self.assertEqual(result.reason, "PAYMENT_VERIFIED_PENDING_DELIVERY")
        self.assertEqual(len(self.flow.ledger.for_order("EB-ORDER-1")), 1)
        with self.assertRaisesRegex(ValueError, "DELIVERY_VERIFICATION_REQUIRED"):
            self.flow.realize_revenue(
                order_id="EB-ORDER-1", evidence=revenue(),
                amount_minor=1250, currency="USD",
            )
        self.assertEqual(self.flow.ledger.for_order("EB-ORDER-1")[-1].to_state, "PAYMENT_VERIFIED")

    def test_duplicate_capture_is_idempotent(self):
        first = self.accept()
        second = self.accept()
        self.assertEqual(first.state, "PAYMENT_VERIFIED")
        self.assertEqual(second.reason, "DUPLICATE_CAPTURE_IGNORED")
        self.assertEqual(len(self.flow.ledger.for_order("EB-ORDER-1")), 1)

    def test_registered_intent_amount_mismatch_blocks_capture(self):
        with self.assertRaisesRegex(ValueError, "CAPTURE_DOES_NOT_MATCH_REGISTERED_INTENT"):
            self.flow.accept_capture(
                response=capture(), order_id="EB-ORDER-1",
                paypal_order_id="PP-ORDER-1", amount="12.51", currency="USD",
            )
        self.assertEqual(self.flow.ledger.for_order("EB-ORDER-1"), [])

    def test_revenue_requires_delivery_then_records_linked_evidence(self):
        self.accept()
        result = self.flow.verify_delivery(order_id="EB-ORDER-1", evidence=delivery())
        self.assertEqual(result.state, "DELIVERY_VERIFIED")
        realized = self.flow.realize_revenue(
            order_id="EB-ORDER-1", evidence=revenue(),
            amount_minor=1250, currency="USD",
        )
        self.assertEqual(realized.state, "REVENUE_REALIZED")
        entries = self.flow.ledger.for_order("EB-ORDER-1")
        self.assertEqual([e.to_state for e in entries], [
            "PAYMENT_VERIFIED", "DELIVERY_VERIFIED", "REVENUE_REALIZED"
        ])
        self.assertEqual(len(entries[-1].evidence_refs), 3)

    def test_delivery_for_wrong_order_is_rejected(self):
        self.accept()
        wrong = Evidence.create(
            evidence_id="delivery:wrong", evidence_type="DELIVERY_VERIFICATION",
            order_id="OTHER-ORDER", source="test", reference="proof",
            payload={"delivered": True},
        )
        with self.assertRaisesRegex(ValueError, "DELIVERY_EVIDENCE_MISMATCH"):
            self.flow.verify_delivery(order_id="EB-ORDER-1", evidence=wrong)
        self.assertEqual(self.flow.ledger.for_order("EB-ORDER-1")[-1].to_state, "PAYMENT_VERIFIED")


if __name__ == "__main__":
    unittest.main()
