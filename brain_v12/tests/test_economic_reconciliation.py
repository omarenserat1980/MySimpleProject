import os
import tempfile
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from brain_v12.brain.economic_reconciliation import router


class EconomicReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "reconciliation.json")
        self.app = FastAPI()
        self.app.include_router(router(self.db))
        self.client = TestClient(self.app)
        self.old = os.environ.get("BRAIN_CONTROL_KEY")
        os.environ["BRAIN_CONTROL_KEY"] = "test-control"

    def tearDown(self):
        if self.old is None:
            os.environ.pop("BRAIN_CONTROL_KEY", None)
        else:
            os.environ["BRAIN_CONTROL_KEY"] = self.old
        self.tmp.cleanup()

    def test_reconcile_requires_control_key(self):
        r = self.client.post("/api/economic-reconciliation/reconcile", json={
            "order_id": "BRAIN-ORD-1",
            "payment_transaction_id": "tx:1",
            "payment_evidence_ref": "pay:1",
            "delivery_evidence_ref": "delivery:1",
            "amount_usd": 9,
        })
        self.assertEqual(r.status_code, 401)

    def test_reconcile_is_idempotent_and_evidence_gated(self):
        payload = {
            "order_id": "BRAIN-ORD-1",
            "payment_transaction_id": "tx:1",
            "payment_evidence_ref": "pay:1",
            "delivery_evidence_ref": "delivery:1",
            "amount_usd": 9,
        }
        r = self.client.post(
            "/api/economic-reconciliation/reconcile",
            json=payload,
            headers={"X-Brain-Control-Key": "test-control"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["state"], "REVENUE_REALIZED")
        r2 = self.client.post(
            "/api/economic-reconciliation/reconcile",
            json=payload,
            headers={"X-Brain-Control-Key": "test-control"},
        )
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["audit_fingerprint"], r.json()["audit_fingerprint"])


if __name__ == "__main__":
    unittest.main()
