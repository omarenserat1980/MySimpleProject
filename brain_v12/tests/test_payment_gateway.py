import json, os, tempfile, time, unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from brain_v12.brain.commerce_api import CommerceStore, CommerceOrderIn
from brain_v12.brain.payment_gateway import signature
class PaymentGatewayTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.db=self.tmp.name+"/commerce.json"; os.environ["BRAIN_COMMERCE_DB"]=self.db; self.secret="test-secret"; os.environ["BRAIN_PAYMENT_WEBHOOK_SECRET"]=self.secret; os.environ["BRAIN_PAYMENT_PROVIDER"]="test"; self.store=CommerceStore(self.db); self.order=self.store.create(CommerceOrderIn(customer_name="Test",contact="test@example.com",product_id="ai-starter-kit")); self.store.transition(self.order["order_id"],"PAYMENT_PENDING","test-pending")
        from brain_v12.brain.payment_gateway import router
        api=FastAPI(); api.include_router(router(self.db)); self.client=TestClient(api)
    def tearDown(self): self.tmp.cleanup(); os.environ.pop("BRAIN_COMMERCE_DB",None); os.environ.pop("BRAIN_PAYMENT_WEBHOOK_SECRET",None); os.environ.pop("BRAIN_PAYMENT_PROVIDER",None)
    def signed(self,payload,ts=None):
        ts=ts or int(time.time()); raw=json.dumps(payload,separators=(",",":")).encode(); return raw,{"X-Brain-Payment-Timestamp":str(ts),"X-Brain-Payment-Signature":signature(self.secret,ts,raw)}
    def test_verified_webhook(self):
        p={"event_id":"evt_12345678","event_type":"payment.verified","order_id":self.order["order_id"],"provider":"test","payment_reference":"pay_123","amount_usd":9,"currency":"USD","timestamp":int(time.time())}; raw,h=self.signed(p); r=self.client.post("/api/payments/webhook",content=raw,headers=h)
        self.assertEqual(r.status_code,200); self.assertEqual(r.json()["state"],"PAYMENT_VERIFIED"); self.assertEqual(r.json()["order_id"],self.order["order_id"]); self.assertEqual(r.json()["payment_reference"],"pay_123")

    def test_signed_webhook_establishes_independent_revenue_authority(self):
        order = self.store.get(self.order["order_id"])
        self.assertNotEqual(order.get("revenue_authority", {}).get("status"), "INDEPENDENTLY_VERIFIED")
        p={"event_id":"evt_authority1","event_type":"payment.verified","order_id":self.order["order_id"],"provider":"test","payment_reference":"pay_authority","amount_usd":9,"currency":"USD","timestamp":int(time.time())}
        raw,h=self.signed(p)
        r=self.client.post("/api/payments/webhook",content=raw,headers=h)
        self.assertEqual(r.status_code,200)
        order = self.store.get(self.order["order_id"])
        self.assertEqual(order["revenue_authority"]["status"], "INDEPENDENTLY_VERIFIED")
        self.assertEqual(order["revenue_authority"]["payment_transaction_id"], "pay_authority")

    def test_replay_rejected(self):
        p={"event_id":"evt_replay1","event_type":"payment.verified","order_id":self.order["order_id"],"provider":"test","payment_reference":"pay_456","amount_usd":9,"currency":"USD","timestamp":int(time.time())}; raw,h=self.signed(p); self.assertEqual(self.client.post("/api/payments/webhook",content=raw,headers=h).status_code,200); self.assertEqual(self.client.post("/api/payments/webhook",content=raw,headers=h).status_code,409)
    def test_journal_recovers_after_commerce_commit_before_replay_record(self):
        p={"event_id":"evt_journal_recover","event_type":"payment.verified","order_id":self.order["order_id"],"provider":"test","payment_reference":"pay_journal","amount_usd":9,"currency":"USD","timestamp":int(time.time())}
        raw,h=self.signed(p)
        from brain_v12.brain.payment_gateway import PaymentEventJournal
        journal_path=self.db + ".payment-events.json"
        journal=PaymentEventJournal(journal_path)
        journal.begin(__import__("brain_v12.brain.payment_gateway", fromlist=["WebhookEnvelope"]).WebhookEnvelope.parse_obj(p))
        journal.mark(p["event_id"], "COMMERCE_COMMITTED")
        second=self.client.post("/api/payments/webhook",content=raw,headers=h)
        self.assertEqual(second.status_code,200)
        self.assertTrue(second.json().get("idempotent"))
        self.assertEqual(second.json()["state"], "PAYMENT_VERIFIED")
        replay_file=self.db + ".webhooks.json"
        with open(replay_file, "r", encoding="utf-8") as f:
            replay_data=json.load(f)
        self.assertIn(p["event_id"], replay_data)

    def test_verified_webhook_is_idempotent_after_replay_record_loss(self):
        p={"event_id":"evt_recover1","event_type":"payment.verified","order_id":self.order["order_id"],"provider":"test","payment_reference":"pay_recover","amount_usd":9,"currency":"USD","timestamp":int(time.time())}
        raw,h=self.signed(p)
        first=self.client.post("/api/payments/webhook",content=raw,headers=h)
        self.assertEqual(first.status_code,200)
        replay_file=self.db + ".webhooks.json"
        os.remove(replay_file)
        second_payload=dict(p); second_payload["event_id"]="evt_recover2"
        raw2,h2=self.signed(second_payload)
        second=self.client.post("/api/payments/webhook",content=raw2,headers=h2)
        self.assertEqual(second.status_code,200)
        self.assertTrue(second.json().get("idempotent"))

    def test_payment_reference_replay_rejected_across_event_ids(self):
        second = self.store.create(CommerceOrderIn(customer_name="Test2",contact="test2@example.com",product_id="ai-starter-kit"))
        self.store.transition(second["order_id"],"PAYMENT_PENDING","test-pending-2")
        p1={"event_id":"evt_ref_a","event_type":"payment.verified","order_id":self.order["order_id"],"provider":"test","payment_reference":"pay_same_ref","amount_usd":9,"currency":"USD","timestamp":int(time.time())}
        raw,h=self.signed(p1)
        self.assertEqual(self.client.post("/api/payments/webhook",content=raw,headers=h).status_code,200)
        p2=dict(p1); p2["event_id"]="evt_ref_b"; p2["order_id"]=second["order_id"]
        raw2,h2=self.signed(p2)
        self.assertEqual(self.client.post("/api/payments/webhook",content=raw2,headers=h2).status_code,409)

    def test_provider_event_identity_is_persisted_in_authority(self):
        p={"event_id":"evt_identity1","event_type":"payment.verified","order_id":self.order["order_id"],"provider":"test","payment_reference":"pay_identity","amount_usd":9,"currency":"USD","timestamp":int(time.time())}
        raw,h=self.signed(p)
        r=self.client.post("/api/payments/webhook",content=raw,headers=h)
        self.assertEqual(r.status_code,200)
        order=self.store.get(self.order["order_id"])
        self.assertEqual(order["revenue_authority"]["provider"],"test")
        self.assertEqual(order["revenue_authority"]["event_id"],"evt_identity1")

    def test_bad_signature_rejected(self):
        p={"event_id":"evt_bad123","event_type":"payment.verified","order_id":self.order["order_id"],"provider":"test","payment_reference":"pay_789","amount_usd":9,"currency":"USD","timestamp":int(time.time())}; raw,_=self.signed(p); r=self.client.post("/api/payments/webhook",content=raw,headers={"X-Brain-Payment-Timestamp":str(int(time.time())),"X-Brain-Payment-Signature":"bad"}); self.assertEqual(r.status_code,401)
if __name__=="__main__": unittest.main()
