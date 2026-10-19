import hashlib
import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.commerce_api import CommerceOrderIn, CommerceStore
from brain_v12.business.commerce_revenue_bridge import CommerceRevenueBridge
from brain_v12.business.revenue_ledger_store import RevenueLedgerStore


class CommerceRevenueBridgeTests(unittest.TestCase):
    def setUp(self):
        import os
        self.old_authority_secret = os.environ.get("BRAIN_PAYMENT_WEBHOOK_SECRET")
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.commerce = CommerceStore(str(root / "commerce.json"))
        self.ledger_path = str(root / "ledger.sqlite")
        self.outbox_path = str(root / "outbox.sqlite")
        self.ledger = RevenueLedgerStore(self.ledger_path)
        self.bridge = CommerceRevenueBridge(self.outbox_path, self.commerce, self.ledger)
        self.order = self.commerce.create(CommerceOrderIn(
            customer_name="Test", contact="test@example.com", product_id="ai-starter-kit"))
        self.order_id = self.order["order_id"]
        self.tx = "paytabs-test-tx"

    def tearDown(self):
        import os
        if self.old_authority_secret is None:
            os.environ.pop("BRAIN_PAYMENT_WEBHOOK_SECRET", None)
        else:
            os.environ["BRAIN_PAYMENT_WEBHOOK_SECRET"] = self.old_authority_secret
        self.ledger.close()
        self.temp.cleanup()

    def _realized_order(self):
        import os
        os.environ["BRAIN_PAYMENT_WEBHOOK_SECRET"] = "test-authority-secret"
        self.commerce.transition(self.order_id, "PAYMENT_PENDING", "checkout")
        self.commerce.transition(self.order_id, "PAYMENT_VERIFIED", {
            "transaction_id": self.tx, "evidence_ref": "paytabs:receipt",
            "independent_verification": "SIGNED_PROVIDER_WEBHOOK", "provider": "paytabs",
            "event_id": self.tx, "authority_proof": __import__("brain_v12.brain.commerce_api", fromlist=["payment_authority_proof"]).payment_authority_proof(
                "test-authority-secret", self.order_id, self.tx, "paytabs", self.tx),
        })
        # The commerce store verifies the supplied proof using the configured secret.
        self.commerce.transition(self.order_id, "DELIVERY_PENDING", "delivery-plan")
        self.commerce.transition(self.order_id, "DELIVERED", "delivery-proof")
        self.commerce.transition(self.order_id, "REVENUE_REALIZED", {
            "delivery_evidence_ref": "delivery-proof", "reconciliation_ref": "reconciliation-proof"})

    def test_event_waits_until_order_is_persistently_realized_then_completes_idempotently(self):
        event = self.bridge.enqueue(self.order_id, self.tx, "delivery-proof", "reconciliation-proof")
        self.assertEqual(event["status"], "PENDING")
        with self.assertRaisesRegex(ValueError, "not durably REVENUE_REALIZED"):
            self.bridge.reconcile(self.order_id, self.tx)
        self.assertEqual(self.bridge.get(self.order_id, self.tx)["status"], "PENDING")
        self._realized_order()
        first = self.bridge.reconcile(self.order_id, self.tx)
        self.assertEqual(first["status"], "COMPLETED")
        self.assertEqual(first["ledger"]["status"], "REVENUE_REALIZED")
        second = self.bridge.reconcile(self.order_id, self.tx)
        self.assertEqual(second["status"], "COMPLETED")
        self.assertEqual(len(second["ledger"]["evidence"]), 2)

    def test_mismatched_authority_keeps_event_pending(self):
        self._realized_order()
        # Replace the authority's transaction in the persisted order to simulate corruption.
        order = self.commerce.get(self.order_id)
        order["revenue_authority"]["payment_transaction_id"] = "other-tx"
        data = {item["order_id"]: item for item in self.commerce.list()}
        data[self.order_id] = order
        self.commerce._write(data)
        self.bridge.enqueue(self.order_id, self.tx, "delivery-proof", "reconciliation-proof")
        with self.assertRaisesRegex(ValueError, "transaction mismatch"):
            self.bridge.reconcile(self.order_id, self.tx)
        self.assertEqual(self.bridge.get(self.order_id, self.tx)["status"], "PENDING")
        self.assertIsNone(self.ledger.get(self.order_id))

    def test_conflicting_duplicate_event_is_rejected(self):
        self.bridge.enqueue(self.order_id, self.tx, "delivery-proof", "reconciliation-proof")
        with self.assertRaisesRegex(ValueError, "conflicting realization request"):
            self.bridge.enqueue(self.order_id, self.tx, "different-delivery", "reconciliation-proof")


if __name__ == "__main__":
    unittest.main()

class CommerceRevenueBridgeApiTests(unittest.TestCase):
    def setUp(self):
        import hashlib
        import hmac
        import json
        import os
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from brain_v12.brain.commerce_api import router
        self._env = {name: os.environ.get(name) for name in (
            "BRAIN_COMMERCE_DB", "BRAIN_CONTROL_KEY", "PAYTABS_SERVER_KEY",
            "BRAIN_PAYMENT_WEBHOOK_SECRET", "BRAIN_REVENUE_LEDGER_DB",
            "BRAIN_COMMERCE_REVENUE_OUTBOX_DB")}
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.db = str(root / "commerce.json")
        os.environ["BRAIN_COMMERCE_DB"] = self.db
        os.environ["BRAIN_CONTROL_KEY"] = "test-control-key"
        os.environ["PAYTABS_SERVER_KEY"] = "test-paytabs-key"
        os.environ["BRAIN_PAYMENT_WEBHOOK_SECRET"] = "test-authority-secret"
        os.environ["BRAIN_REVENUE_LEDGER_DB"] = str(root / "ledger.sqlite")
        os.environ["BRAIN_COMMERCE_REVENUE_OUTBOX_DB"] = str(root / "outbox.sqlite")
        app = FastAPI()
        app.include_router(router(self.db))
        self.client = TestClient(app)
        self._hmac = hmac
        self._json = json

    def tearDown(self):
        import os
        for name, value in self._env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        self.temp.cleanup()

    def test_api_realization_reconciles_durable_ledger(self):
        created = self.client.post("/api/commerce/orders", json={
            "customer_name": "Test", "contact": "test@example.com", "product_id": "ai-starter-kit"})
        self.assertEqual(created.status_code, 200, created.text)
        order_id = created.json()["order"]["order_id"]
        headers = {"X-Brain-Control-Key": "test-control-key"}
        self.assertEqual(self.client.post(f"/api/commerce/orders/{order_id}/payment-pending",
            json={"evidence_ref": "checkout"}).status_code, 200)
        payload = {"cart_id": order_id, "cart_amount": "9.00", "cart_currency": "USD",
                   "tran_type": "sale", "payment_result": {"response_status": "A"},
                   "tran_ref": "API-TEST-TX-001"}
        raw = self._json.dumps(payload, separators=(",", ":")).encode()
        signature = self._hmac.new(b"test-paytabs-key", raw, hashlib.sha256).hexdigest()
        verified = self.client.post(f"/api/commerce/orders/{order_id}/paytabs-webhook", content=raw,
            headers={"signature": signature, "content-type": "application/json"})
        self.assertEqual(verified.status_code, 200, verified.text)
        self.assertEqual(self.client.post(f"/api/commerce/orders/{order_id}/delivery-pending",
            headers=headers, json={"evidence_ref": "delivery-plan"}).status_code, 200)
        self.assertEqual(self.client.post(f"/api/commerce/orders/{order_id}/delivered",
            headers=headers, json={"evidence_ref": "delivery-proof"}).status_code, 200)
        realized = self.client.post(f"/api/commerce/orders/{order_id}/revenue-realized", headers=headers,
            json={"delivery_evidence_ref": "delivery-proof", "reconciliation_ref": "reconciliation-proof"})
        self.assertEqual(realized.status_code, 200, realized.text)
        body = realized.json()
        self.assertEqual(body["revenue_ledger_reconciliation"]["status"], "COMPLETED")
        self.assertEqual(body["revenue_ledger_reconciliation"]["ledger"]["status"], "REVENUE_REALIZED")
        self.assertEqual(len(body["revenue_ledger_reconciliation"]["ledger"]["evidence"]), 2)
        recovery = self.client.post("/api/commerce/revenue-reconciliation/run", headers=headers)
        self.assertEqual(recovery.status_code, 200, recovery.text)
        self.assertEqual(recovery.json()["reconciliation"]["processed"], 0)
