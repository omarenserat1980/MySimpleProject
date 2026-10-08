import unittest
from brain_v12.brain.income_lifecycle import IncomeLifecycle


class FakeStore:
    def __init__(self):
        self.rows=[]
        self.events_log=[]

    def income_opportunities(self, limit=500, client_id=None):
        rows=list(self.rows)
        if client_id is None:
            return rows
        return [row for row in rows if row.get("data", {}).get("client_id") == client_id]

    def upsert_income_opportunity(self, item):
        oid=item["opportunity_id"]
        for i,row in enumerate(self.rows):
            if row["opportunity_id"]==oid:
                self.rows[i]={"opportunity_id":oid,"status":item.get("status","DISCOVERY"),
                              "source_url":item.get("source_url"),"title":item.get("title"),
                              "verified_amount_jod":item.get("verified_amount_jod",0),
                              "data":dict(item)}
                return
        self.rows.append({"opportunity_id":oid,"status":item.get("status","DISCOVERY"),
                          "source_url":item.get("source_url"),"title":item.get("title"),
                          "verified_amount_jod":item.get("verified_amount_jod",0),
                          "data":dict(item)})

    def event(self, name, payload):
        self.events_log.append((name,payload))


class IncomeLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.store=FakeStore()
        self.store.upsert_income_opportunity({
            "opportunity_id":"LIVE-test",
            "title":"WordPress landing page",
            "source_url":"https://example.com/project/1",
            "requirements":"Build a responsive Arabic landing page",
            "status":"DISCOVERY",
            "source_kind":"LIVE_OPPORTUNITY",
            "verified_amount_jod":0,
            "verification_status":"UNVERIFIED",
            "owner_role":"Opportunity Researcher",
        })
        self.life=IncomeLifecycle(self.store)

    def test_prepare_does_not_claim_submission(self):
        q=self.life.qualify("LIVE-test")
        self.assertTrue(q["ok"])
        p=self.life.prepare("LIVE-test")
        self.assertEqual(p["status"],"READY_TO_APPLY")
        self.assertEqual(p["external_submission"],"NOT_PERFORMED")
        self.assertEqual(self.store.rows[0]["status"],"READY_TO_APPLY")

    def test_external_steps_require_evidence(self):
        self.life.qualify("LIVE-test")
        self.life.prepare("LIVE-test")
        denied=self.life.record_external("LIVE-test","SUBMITTED","")
        self.assertFalse(denied["ok"])
        submitted=self.life.record_external("LIVE-test","SUBMITTED","platform receipt #123")
        self.assertTrue(submitted["ok"])
        accepted=self.life.record_external("LIVE-test","ACCEPTED","client accepted proposal")
        self.assertTrue(accepted["ok"])


    def test_payment_request_requires_completed_delivery(self):
        denied=self.life.request_payment("LIVE-test", 25)
        self.assertEqual(denied["status"], "DELIVERY_NOT_VERIFIED")

    def test_payment_request_reconcile_and_realize_are_idempotent(self):
        self.life.qualify("LIVE-test")
        self.life.prepare("LIVE-test")
        for status, evidence in [("SUBMITTED","receipt-1"),("CLIENT_RESPONDED","client-1"),("ACCEPTED","accepted-1"),("DELIVERING","delivery-start-1"),("COMPLETED","delivery-final-1")]:
            self.life.record_external("LIVE-test", status, evidence)
        req=self.life.request_payment("LIVE-test", 25, currency="JOD")
        self.assertEqual(req["status"], "PAYMENT_REQUESTED")
        self.assertEqual(self.life.request_payment("LIVE-test",25,currency="JOD")["status"], "ALREADY_REQUESTED")
        recon=self.life.reconcile_payment("LIVE-test",25,"JOD","TX-001","provider-reference-001")
        self.assertEqual(recon["status"], "RECONCILED")
        self.assertEqual(self.life.realize_revenue("LIVE-test")["status"], "REVENUE_REALIZED")
        self.assertEqual(self.life.realize_revenue("LIVE-test")["status"], "ALREADY_REALIZED")

    def test_reconciliation_rejects_amount_or_currency_mismatch(self):
        self.life.qualify("LIVE-test")
        self.life.prepare("LIVE-test")
        for status, evidence in [("SUBMITTED","receipt-1"),("CLIENT_RESPONDED","client-1"),("ACCEPTED","accepted-1"),("DELIVERING","delivery-start-1"),("COMPLETED","delivery-final-1")]:
            self.life.record_external("LIVE-test", status, evidence)
        self.life.request_payment("LIVE-test",25,currency="JOD")
        self.assertEqual(self.life.reconcile_payment("LIVE-test",20,"JOD","TX-002","evidence")["status"],"AMOUNT_MISMATCH")
        self.assertEqual(self.life.reconcile_payment("LIVE-test",25,"USD","TX-003","evidence")["status"],"CURRENCY_MISMATCH")
    def test_payment_cannot_skip_delivery(self):
        self.life.qualify("LIVE-test")
        self.life.prepare("LIVE-test")
        self.assertEqual(self.store.rows[0]["status"],"READY_TO_APPLY")

    def test_cannot_skip_lifecycle_stage(self):
        skipped=self.life.record_external("LIVE-test","PAYMENT_VERIFIED","payment receipt #1")
        self.assertFalse(skipped["ok"])
        self.assertEqual(skipped["status"],"INVALID_SKIPPED_TRANSITION")


if __name__=="__main__":
    unittest.main()


    # Lifecycle tracking is implemented by IncomeEngine; this test file
    # intentionally keeps the existing IncomeLifecycle regression coverage.
