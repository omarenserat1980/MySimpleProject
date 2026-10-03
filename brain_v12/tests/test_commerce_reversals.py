import os
import tempfile
import unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from brain_v12.brain.commerce_api import router as commerce_router
from brain_v12.brain.commerce_reversals import router as reversal_router

class CommerceReversalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.NamedTemporaryFile(delete=False); self.tmp.close(); self.db=self.tmp.name
        self.old_db=os.environ.get("BRAIN_COMMERCE_DB"); os.environ["BRAIN_COMMERCE_DB"]=self.db; os.environ["BRAIN_CONTROL_KEY"]="test-control"
        app=FastAPI(); app.include_router(commerce_router(self.db)); app.include_router(reversal_router(self.db)); self.client=TestClient(app)
    def tearDown(self):
        if self.old_db is None: os.environ.pop("BRAIN_COMMERCE_DB",None)
        else: os.environ["BRAIN_COMMERCE_DB"]=self.old_db
        try: os.unlink(self.db)
        except FileNotFoundError: pass
    def _headers(self): return {"X-Brain-Control-Key":"test-control"}
    def _create_delivered(self):
        r=self.client.post("/api/commerce/orders",json={"customer_name":"Test Customer","contact":"test@example.com","product_id":"ai-starter-kit","details":"reversal test"})
        oid=r.json()["order"]["order_id"]
        self.client.post(f"/api/commerce/orders/{oid}/payment-pending",json={"evidence_ref":"order-evidence"})
        self.client.post(f"/api/commerce/orders/{oid}/payment-verified",headers=self._headers(),json={"evidence_ref":"payment-evidence","transaction_id":"tx:reversal"})
        self.client.post(f"/api/commerce/orders/{oid}/delivery-pending",headers=self._headers(),json={"evidence_ref":"delivery-plan"})
        r=self.client.post(f"/api/commerce/orders/{oid}/delivered",headers=self._headers(),json={"evidence_ref":"delivery-proof"})
        self.assertEqual(r.status_code,200); return oid
    def test_refund_requires_evidence_and_records_without_money_movement(self):
        oid=self._create_delivered(); r=self.client.post(f"/api/commerce/reversals/{oid}/refund-request",headers=self._headers(),json={"evidence_ref":"customer-refund-request","reason":"customer request"})
        self.assertEqual(r.status_code,200); body=r.json()["order"]; self.assertEqual(body["refund"]["status"],"REQUESTED"); self.assertFalse(body["refund"]["money_movement"])
        r=self.client.post(f"/api/commerce/reversals/{oid}/refund-approved",headers=self._headers(),json={"evidence_ref":"refund-approval-evidence"})
        self.assertEqual(r.status_code,200); self.assertEqual(r.json()["order"]["refund"]["status"],"APPROVED"); self.assertFalse(r.json()["order"]["refund"]["money_movement"])
    def test_dispute_lifecycle_is_audited(self):
        oid=self._create_delivered(); r=self.client.post(f"/api/commerce/reversals/{oid}/dispute-open",headers=self._headers(),json={"evidence_ref":"dispute-evidence","reason":"chargeback notice"})
        self.assertEqual(r.status_code,200); self.assertEqual(r.json()["order"]["dispute"]["status"],"OPEN")
        r=self.client.post(f"/api/commerce/reversals/{oid}/dispute-closed",headers=self._headers(),json={"evidence_ref":"resolution-evidence"})
        self.assertEqual(r.status_code,200); self.assertEqual(r.json()["order"]["dispute"]["status"],"CLOSED")
    def test_control_key_is_required(self):
        oid=self._create_delivered(); r=self.client.post(f"/api/commerce/reversals/{oid}/refund-request",json={"evidence_ref":"x"}); self.assertEqual(r.status_code,403)
if __name__=="__main__": unittest.main()
