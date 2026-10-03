import hashlib, hmac, json, os, tempfile, time, unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from brain_v12.brain.commerce_api import CommerceStore, CommerceOrderIn
from brain_v12.brain.payment_gateway import signature

class PaymentGatewayTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=self.tmp.name+"/commerce.json"
        os.environ["BRAIN_COMMERCE_DB"]=self.db
        self.secret="test-secret"
        os.environ["BRAIN_PAYMENT_WEBHOOK_SECRET"]=self.secret
        self.store=CommerceStore(self.db)
        self.order=self.store.create(CommerceOrderIn(customer_name="Test",contact="test@example.com",product_id="ai-starter-kit"))
        self.store.transition(self.order["order_id"],"PAYMENT_PENDING","test-pending")
        from brain_v12.brain.payment_gateway import router
        api=FastAPI()
        api.include_router(router(self.db))
        self.client=TestClient(api)
    def tearDown(self):
        self.tmp.cleanup()
        os.environ.pop("BRAIN_COMMERCE_DB",None)
        os.environ.pop("BRAIN_PAYMENT_WEBHOOK_SECRET",None)
    def signed(self,payload,ts=None):
        ts=ts or int(time.time())
        raw=json.dumps(payload,separators=(",",":")).encode()
        return raw, {"X-Brain-Payment-Timestamp":str(ts),"X-Brain-Payment-Signature":signature(self.secret,ts,raw)}
    def test_verified_webhook(self):
        p={"event_id":"evt_12345678","event_type":"payment.verified","order_id":self.order["order_id"],"provider":"test","payment_reference":"pay_123","amount_usd":9,"currency":"USD","timestamp":int(time.time())}
        raw,h=self.signed(p)
        r=self.client.post("/api/payments/webhook",content=raw,headers=h)
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json()["state"],"PAYMENT_VERIFIED")
        payment=r.json()["order"]["payment"]
        self.assertEqual(payment["transaction_id"],"pay_123")
        self.assertEqual(payment["evidence_ref"],"payment-webhook:test:evt_12345678")
    def test_replay_rejected(self):
        p={"event_id":"evt_replay1","event_type":"payment.verified","order_id":self.order["order_id"],"provider":"test","payment_reference":"pay_456","amount_usd":9,"currency":"USD","timestamp":int(time.time())}
        raw,h=self.signed(p)
        self.assertEqual(self.client.post("/api/payments/webhook",content=raw,headers=h).status_code,200)
        self.assertEqual(self.client.post("/api/payments/webhook",content=raw,headers=h).status_code,409)
    def test_bad_signature_rejected(self):
        p={"event_id":"evt_bad123","event_type":"payment.verified","order_id":self.order["order_id"],"provider":"test","payment_reference":"pay_789","amount_usd":9,"currency":"USD","timestamp":int(time.time())}
        raw,_=self.signed(p)
        r=self.client.post("/api/payments/webhook",content=raw,headers={"X-Brain-Payment-Timestamp":str(int(time.time())),"X-Brain-Payment-Signature":"bad"})
        self.assertEqual(r.status_code,401)

if __name__=="__main__": unittest.main()
