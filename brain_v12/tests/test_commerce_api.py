import hashlib
import hmac
import json
import os
import tempfile
import unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient
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
            with self.assertRaises(Exception) as spoof:
                s.transition(oid, "PAYMENT_VERIFIED", {
                    "transaction_id": "tx-spoof",
                    "evidence_ref": "caller-claimed-receipt",
                    "provider": "test",
                    "event_id": "evt_spoof123",
                    "independent_verification": "SIGNED_PROVIDER_WEBHOOK",
                })
            self.assertEqual(getattr(spoof.exception, "status_code", None), 403)
            self.assertEqual(s.get(oid)["state"], "PAYMENT_PENDING")
            s.transition(oid, "PAYMENT_VERIFIED", {"transaction_id": "tx-smoke", "evidence_ref": "provider-receipt:smoke"})
            s.transition(oid, "DELIVERY_PENDING", "delivery-request:smoke")
            s.transition(oid, "DELIVERED", "delivery-proof:smoke")
            with self.assertRaises(Exception) as ctx:
                s.transition(oid, "REVENUE_REALIZED", {"delivery_evidence_ref": "delivery-proof:smoke", "reconciliation_ref": "reconciliation:smoke"})
            self.assertEqual(getattr(ctx.exception, "detail", str(ctx.exception)), "REVENUE_AUTHORITY_REQUIRED")
            self.assertEqual(s.get(oid)["state"], "DELIVERED")

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


class PayTabsCommerceWebhookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.temp.name) / "commerce.json")
        self.previous_db = os.environ.get("BRAIN_COMMERCE_DB")
        self.previous_paytabs_key = os.environ.get("PAYTABS_SERVER_KEY")
        self.previous_authority_secret = os.environ.get("BRAIN_PAYMENT_WEBHOOK_SECRET")
        os.environ["BRAIN_COMMERCE_DB"] = self.db
        os.environ["PAYTABS_SERVER_KEY"] = "TEST_PAYTABS_KEY_ONLY"
        os.environ["BRAIN_PAYMENT_WEBHOOK_SECRET"] = "TEST_BRAIN_AUTHORITY_SECRET_ONLY"
        app = FastAPI()
        app.include_router(commerce_router(self.db))
        self.client = TestClient(app)

    def tearDown(self):
        for name, old in (
            ("BRAIN_COMMERCE_DB", self.previous_db),
            ("PAYTABS_SERVER_KEY", self.previous_paytabs_key),
            ("BRAIN_PAYMENT_WEBHOOK_SECRET", self.previous_authority_secret),
        ):
            if old is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = old
        self.temp.cleanup()

    def _pending_order(self):
        response = self.client.post("/api/commerce/orders", json={
            "customer_name": "Test Customer",
            "contact": "test@example.com",
            "product_id": "ai-starter-kit",
        })
        self.assertEqual(response.status_code, 200)
        order_id = response.json()["order"]["order_id"]
        pending = self.client.post(
            f"/api/commerce/orders/{order_id}/payment-pending",
            json={"evidence_ref": "test-checkout-intent"},
        )
        self.assertEqual(pending.status_code, 200)
        return order_id

    def _callback(self, order_id, *, tran_type="sale", signature_override=None):
        payload = {
            "cart_id": order_id,
            "cart_amount": "9.00",
            "cart_currency": "USD",
            "tran_type": tran_type,
            "payment_result": {"response_status": "A"},
            "tran_ref": "PAYTABS-TEST-TX-001",
        }
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        sig = hmac.new(b"TEST_PAYTABS_KEY_ONLY", raw, hashlib.sha256).hexdigest()
        if signature_override is not None:
            sig = signature_override
        return self.client.post(
            f"/api/commerce/orders/{order_id}/paytabs-webhook",
            content=raw,
            headers={"signature": sig, "content-type": "application/json"},
        )

    def test_signed_captured_sale_creates_order_bound_authority(self):
        order_id = self._pending_order()
        response = self._callback(order_id)
        self.assertEqual(response.status_code, 200, response.text)
        order = response.json()["order"]
        self.assertEqual(order["state"], "PAYMENT_VERIFIED")
        authority = order["revenue_authority"]
        self.assertEqual(authority["provider"], "paytabs")
        self.assertEqual(authority["order_id"], order_id)
        self.assertEqual(authority["payment_transaction_id"], "PAYTABS-TEST-TX-001")
        self.assertTrue(authority["event_id"])

    def test_invalid_provider_signature_does_not_change_order(self):
        order_id = self._pending_order()
        response = self._callback(order_id, signature_override="0" * 64)
        self.assertEqual(response.status_code, 400)
        order = CommerceStore(self.db).get(order_id)
        self.assertEqual(order["state"], "PAYMENT_PENDING")
        self.assertNotIn("revenue_authority", order)

    def test_authorization_only_callback_is_rejected(self):
        order_id = self._pending_order()
        response = self._callback(order_id, tran_type="auth")
        self.assertEqual(response.status_code, 400)
        self.assertIn("PAYTABS_CAPTURED_SALE_REQUIRED", response.text)
