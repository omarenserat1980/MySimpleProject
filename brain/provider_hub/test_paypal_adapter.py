import os
import unittest
from unittest.mock import patch

from brain.provider_hub.paypal_adapter import PayPalAdapter, PayPalConfig


class FakeTransport:
    def __init__(self):
        self.calls = []

    def __call__(self, url, method, headers, payload):
        self.calls.append((url, method, headers, payload))
        if url.endswith("/v1/oauth2/token"):
            return {"access_token": "test-token"}
        if url.endswith("/v2/checkout/orders"):
            return {"id": "ORDER-SANDBOX-1", "status": "CREATED"}
        if url.endswith("/capture"):
            return {"id": "ORDER-SANDBOX-1", "status": "COMPLETED"}
        raise AssertionError("unexpected endpoint")


class PayPalAdapterTests(unittest.TestCase):
    def setUp(self):
        self.transport = FakeTransport()
        self.adapter = PayPalAdapter(
            PayPalConfig("client-test", "secret-test"), self.transport
        )

    def test_create_order_uses_sandbox_and_exact_amount(self):
        result = self.adapter.create_order(
            order_id="EB-100", amount="12.5", currency="usd",
            return_url="https://example.test/return",
            cancel_url="https://example.test/cancel",
        )
        self.assertEqual(result["status"], "CREATED")
        url, _, _, payload = self.transport.calls[-1]
        self.assertEqual(url, "https://api-m.sandbox.paypal.com/v2/checkout/orders")
        self.assertEqual(payload["purchase_units"][0]["reference_id"], "EB-100")
        self.assertEqual(payload["purchase_units"][0]["amount"],
                         {"currency_code": "USD", "value": "12.50"})

    def test_rejects_invalid_amount(self):
        for amount in ("0", "-1", "NaN", "1.001", "abc"):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                self.adapter.create_order(
                    order_id="EB-101", amount=amount, currency="USD",
                    return_url="https://example.test/return",
                    cancel_url="https://example.test/cancel",
                )
        self.assertEqual(self.transport.calls, [])

    def test_rejects_non_https_return_url(self):
        with self.assertRaisesRegex(ValueError, "HTTPS_RETURN_URLS_REQUIRED"):
            self.adapter.create_order(
                order_id="EB-102", amount="1.00", currency="USD",
                return_url="http://example.test/return",
                cancel_url="https://example.test/cancel",
            )
        self.assertEqual(self.transport.calls, [])

    def test_capture_uses_sandbox_endpoint(self):
        result = self.adapter.capture_order(paypal_order_id="ORDER-SANDBOX-1")
        self.assertEqual(result["status"], "COMPLETED")
        self.assertTrue(self.transport.calls[-1][0].endswith(
            "/v2/checkout/orders/ORDER-SANDBOX-1/capture"))

    def test_environment_requires_both_secrets(self):
        with patch.dict(os.environ, {"PAYPAL_CLIENT_ID": "", "PAYPAL_CLIENT_SECRET": ""}):
            with self.assertRaisesRegex(RuntimeError, "PAYPAL_CLIENT_ID_MISSING"):
                PayPalConfig.from_environment()


if __name__ == "__main__":
    unittest.main()
