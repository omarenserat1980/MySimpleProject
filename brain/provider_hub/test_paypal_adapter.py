import os
import unittest
from unittest.mock import patch
from io import BytesIO

from brain.provider_hub.paypal_adapter import http_transport

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
        if url.endswith("/v1/notifications/verify-webhook-signature"):
            return {"verification_status": "SUCCESS"}
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

    def test_capture_order_id_is_url_encoded(self):
        self.adapter.capture_order(paypal_order_id="ORDER/with space")
        self.assertTrue(self.transport.calls[-1][0].endswith(
            "/v2/checkout/orders/ORDER%2Fwith%20space/capture"))

    def test_http_transport_encodes_oauth_form_body(self):
        response = BytesIO(b'{"access_token":"safe-test-token"}')
        with patch("brain.provider_hub.paypal_adapter.urlopen", return_value=response) as open_url:
            result = http_transport(
                "https://api-m.sandbox.paypal.com/v1/oauth2/token", "POST",
                {"Content-Type": "application/x-www-form-urlencoded"},
                {"grant_type": "client_credentials"},
            )
        self.assertEqual(result["access_token"], "safe-test-token")
        request = open_url.call_args.args[0]
        self.assertEqual(request.data, b"grant_type=client_credentials")
        self.assertEqual(request.get_header("Content-type"), "application/x-www-form-urlencoded")

    def test_webhook_verification_requires_paypal_success(self):
        headers = {
            "PAYPAL-AUTH-ALGO": "SHA256withRSA",
            "PAYPAL-CERT-URL": "https://api-m.sandbox.paypal.com/cert",
            "PAYPAL-TRANSMISSION-ID": "transmission-1",
            "PAYPAL-TRANSMISSION-SIG": "signature",
            "PAYPAL-TRANSMISSION-TIME": "2026-10-13T17:00:00Z",
        }
        event = {"id": "WH-1", "event_type": "PAYMENT.CAPTURE.COMPLETED"}
        result = self.adapter.verify_webhook_event(
            webhook_id="WH-ID", headers=headers, event=event
        )
        self.assertEqual(result["verification_status"], "SUCCESS")

    def test_webhook_verification_rejects_missing_headers(self):
        with self.assertRaisesRegex(ValueError, "PAYPAL_WEBHOOK_HEADERS_MISSING"):
            self.adapter.verify_webhook_event(
                webhook_id="WH-ID", headers={}, event={"id": "WH-1", "event_type": "TEST"}
            )
        self.assertEqual(self.transport.calls, [])

    def test_environment_requires_both_secrets(self):
        with patch.dict(os.environ, {"PAYPAL_CLIENT_ID": "", "PAYPAL_CLIENT_SECRET": ""}):
            with self.assertRaisesRegex(RuntimeError, "PAYPAL_CLIENT_ID_MISSING"):
                PayPalConfig.from_environment()


if __name__ == "__main__":
    unittest.main()
