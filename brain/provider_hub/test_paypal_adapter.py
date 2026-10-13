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


    def test_validate_capture_requires_exact_order_amount_currency_and_capture(self):
        response = {
            "id": "PAYPAL-ORDER-1", "status": "COMPLETED",
            "purchase_units": [{
                "reference_id": "EB-200", "invoice_id": "EB-200",
                "payments": {"captures": [{
                    "id": "CAPTURE-1", "status": "COMPLETED",
                    "amount": {"value": "12.50", "currency_code": "USD"},
                }]},
            }],
        }
        evidence = PayPalAdapter.validate_capture(
            response=response, expected_order_id="EB-200",
            expected_paypal_order_id="PAYPAL-ORDER-1",
            expected_amount="12.50", expected_currency="USD",
        )
        self.assertEqual(evidence["capture_id"], "CAPTURE-1")
        ambiguous = {
            **response,
            "purchase_units": [{
                **response["purchase_units"][0],
                "payments": {"captures": [
                    response["purchase_units"][0]["payments"]["captures"][0],
                    {**response["purchase_units"][0]["payments"]["captures"][0], "id": "CAPTURE-2"},
                ]},
            }],
        }
        with self.assertRaisesRegex(ValueError, "PAYPAL_CAPTURE_EVIDENCE_MISSING_OR_AMBIGUOUS"):
            PayPalAdapter.validate_capture(
                response=ambiguous, expected_order_id="EB-200",
                expected_paypal_order_id="PAYPAL-ORDER-1",
                expected_amount="12.50", expected_currency="USD",
            )
        for kwargs, error in (
            ({"expected_amount": "12.51"}, "PAYPAL_CAPTURE_AMOUNT_MISMATCH"),
            ({"expected_currency": "EUR"}, "PAYPAL_CAPTURE_CURRENCY_MISMATCH"),
            ({"expected_order_id": "EB-OTHER"}, "PAYPAL_MERCHANT_ORDER_MISMATCH"),
            ({"expected_paypal_order_id": "OTHER"}, "PAYPAL_ORDER_ID_MISMATCH"),
        ):
            args = {
                "response": response, "expected_order_id": "EB-200",
                "expected_paypal_order_id": "PAYPAL-ORDER-1",
                "expected_amount": "12.50", "expected_currency": "USD",
            }
            args.update(kwargs)
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                PayPalAdapter.validate_capture(**args)

    def test_environment_requires_both_secrets(self):
        with patch.dict(os.environ, {"PAYPAL_CLIENT_ID": "", "PAYPAL_CLIENT_SECRET": ""}):
            with self.assertRaisesRegex(RuntimeError, "PAYPAL_CLIENT_ID_MISSING"):
                PayPalConfig.from_environment()


if __name__ == "__main__":
    unittest.main()
