import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from brain_v12.brain.commerce_api import router as commerce_router
from brain_v12.brain.commerce_documents import router as documents_router


class CommerceDocumentsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "commerce.json")
        app = FastAPI()
        app.include_router(commerce_router(self.db))
        app.include_router(documents_router(self.db))
        self.client = TestClient(app)
        self.headers = {"X-Brain-Control-Key": "test-control"}

        import os
        os.environ["BRAIN_CONTROL_KEY"] = "test-control"

    def tearDown(self):
        self.tmp.cleanup()

    def _delivered_order(self):
        r = self.client.post("/api/commerce/orders", json={
            "customer_name": "Test Customer",
            "contact": "test@example.com",
            "product_id": "ai-starter-kit",
        })
        order = r.json()["order"]
        oid = order["order_id"]
        self.client.post(f"/api/commerce/orders/{oid}/payment-pending", json={"evidence_ref":"checkout:test"})
        self.client.post(f"/api/commerce/orders/{oid}/payment-verified", headers=self.headers, json={"evidence_ref":"provider:test"})
        self.client.post(f"/api/commerce/orders/{oid}/delivery-pending", headers=self.headers, json={"evidence_ref":"delivery-request:test"})
        self.client.post(f"/api/commerce/orders/{oid}/delivered", headers=self.headers, json={"evidence_ref":"delivery:test"})
        return oid

    def test_invoice_requires_verified_payment(self):
        r = self.client.post("/api/commerce/orders", json={
            "customer_name": "Test Customer",
            "contact": "test@example.com",
            "product_id": "media-toolkit",
        })
        oid = r.json()["order"]["order_id"]
        response = self.client.get(f"/api/commerce/documents/orders/{oid}/invoice", headers=self.headers)
        self.assertEqual(response.status_code, 409)

    def test_invoice_and_receipt_are_evidence_backed(self):
        oid = self._delivered_order()
        invoice = self.client.get(f"/api/commerce/documents/orders/{oid}/invoice", headers=self.headers)
        receipt = self.client.get(f"/api/commerce/documents/orders/{oid}/receipt", headers=self.headers)
        self.assertEqual(invoice.status_code, 200)
        self.assertEqual(receipt.status_code, 200)
        self.assertEqual(invoice.json()["invoice"]["amount_usd"], 9)
        self.assertEqual(receipt.json()["receipt"]["payment_evidence_ref"], "provider:test")
        self.assertTrue(invoice.json()["invoice"]["document_fingerprint"])
        self.assertTrue(receipt.json()["receipt"]["document_fingerprint"])


if __name__ == "__main__":
    unittest.main()
