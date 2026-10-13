import unittest

from brain.provider_hub.paypal_evidence_bridge import PayPalEvidenceBridge


def completed_capture():
    return {
        "id": "PAYPAL-ORDER-42",
        "status": "COMPLETED",
        "purchase_units": [{
            "reference_id": "EB-42",
            "invoice_id": "EB-42",
            "payments": {"captures": [{
                "id": "CAPTURE-42",
                "status": "COMPLETED",
                "amount": {"value": "7.25", "currency_code": "USD"},
            }]},
        }],
    }


class PayPalEvidenceBridgeTests(unittest.TestCase):
    def test_reconciled_capture_becomes_payment_evidence(self):
        result = PayPalEvidenceBridge.from_capture(
            response=completed_capture(),
            order_id="EB-42",
            paypal_order_id="PAYPAL-ORDER-42",
            amount="7.25",
            currency="USD",
        )
        self.assertEqual(result.capture_id, "CAPTURE-42")
        self.assertEqual(result.evidence.evidence_id, "paypal:capture:CAPTURE-42")
        self.assertEqual(result.evidence.evidence_type, "PAYMENT_VERIFICATION")
        self.assertEqual(result.evidence.order_id, "EB-42")
        self.assertEqual(result.evidence.source, "paypal")
        self.assertEqual(result.evidence.payload["amount"], "7.25")

    def test_mismatched_amount_never_becomes_evidence(self):
        with self.assertRaisesRegex(ValueError, "PAYPAL_CAPTURE_AMOUNT_MISMATCH"):
            PayPalEvidenceBridge.from_capture(
                response=completed_capture(),
                order_id="EB-42",
                paypal_order_id="PAYPAL-ORDER-42",
                amount="7.26",
                currency="USD",
            )

    def test_mismatched_merchant_order_never_becomes_evidence(self):
        with self.assertRaisesRegex(ValueError, "PAYPAL_MERCHANT_ORDER_MISMATCH"):
            PayPalEvidenceBridge.from_capture(
                response=completed_capture(),
                order_id="EB-OTHER",
                paypal_order_id="PAYPAL-ORDER-42",
                amount="7.25",
                currency="USD",
            )


if __name__ == "__main__":
    unittest.main()
