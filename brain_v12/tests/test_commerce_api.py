import hashlib
import hmac
import json
import os
import tempfile
import unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pathlib import Path

from brain_v12.brain.commerce_api import CommerceOrderIn, CommerceStore, router as commerce_router


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
        self.old_db = os.environ.get("BRAIN_COMMERCE_DB")
        self.old_key = os.environ.get("PAYTABS_SERVER_KEY")
        os.environ["BRAIN_COMMERCE_DB"] = self.db
        os.environ["PAYTABS_SERVER_KEY"] = "TEST_ONLY_SECRET"
        app = FastAPI()
        app.include_router(commerce_router(self.db))
        self.client = TestClient(app)

    def tearDown(self):
        if self.old_db is None:
            os.environ.pop("BRAIN_COMMERCE_DB", None)
        else:
            os.environ["BRAIN_COMMERCE_DB"] = self.old_db
        if self.old_key is None:
            os.environ.pop("PAYTABS_SERVER_KEY", None)
        else:
            os.environ["PAYTABS_SERVER_KEY"] = self.old_key
        self.temp.cleanup()

    def _create_pending_order(self):
        response = self.client.post("/api/commerce/orders", json={
            "customer_name": "Test Customer",
            "contact": "test@example.com",
            "product_id": "ai-starter-kit",
        })
        self.assertEqual(response.status_code, 200)
        order = response.json()["order"]
        pending = self.client.post(
            f"/api/commerce/orders/{order['order_id']}/payment-pending",
            json={"evidence_ref": "checkout-test"},
        )
        self.assertEqual(pending.status_code, 200)
        return order["order_id"]

    def _callback(self, order_id, amount="9.00"):
        body = json.dumps({
            "cart_id": order_id,
            "cart_amount": amount,
            "cart_currency": "USD",
            "payment_result": {"response_status": "A"},
            "tran_ref": "TX-TEST-001",
        }, separators=(",", ":")).encode()
        signature = hmac.new(b"TEST_ONLY_SECRET", body, hashlib.sha256).hexdigest()
        return body, signature

    def test_signed_paytabs_callback_sets_provider_authority_and_is_idempotent(self):
        order_id = self._create_pending_order()
        body, signature = self._callback(order_id)
        url = f"/api/commerce/orders/{order_id}/paytabs-webhook"
        first = self.client.post(url, content=body, headers={"signature": signature})
        self.assertEqual(first.status_code, 200, first.text)
        self.assertFalse(first.json()["duplicate"])
        order = first.json()["order"]
        self.assertEqual(order["payment"]["transaction_id"], "TX-TEST-001")
        self.assertEqual(order["revenue_authority"]["status"], "INDEPENDENTLY_VERIFIED")
        self.assertEqual(order["revenue_authority"]["provider"], "paytabs")
        second = self.client.post(url, content=body, headers={"signature": signature})
        self.assertEqual(second.status_code, 200, second.text)
        self.assertTrue(second.json()["duplicate"])

    def test_invalid_signature_cannot_verify_payment(self):
        order_id = self._create_pending_order()
        body, _ = self._callback(order_id)
        response = self.client.post(
            f"/api/commerce/orders/{order_id}/paytabs-webhook",
            content=body,
            headers={"signature": "0" * 64},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "INVALID_PAYTABS_SIGNATURE")

    def test_amount_mismatch_cannot_verify_payment(self):
        order_id = self._create_pending_order()
        body, signature = self._callback(order_id, amount="90.00")
        response = self.client.post(
            f"/api/commerce/orders/{order_id}/paytabs-webhook",
            content=body,
            headers={"signature": signature},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "PAYTABS_AMOUNT_MISMATCH")
