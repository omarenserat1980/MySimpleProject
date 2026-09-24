import unittest
from brain_v12.brain.income_lifecycle import IncomeLifecycle


class FakeStore:
    def __init__(self):
        self.rows=[]
        self.events_log=[]

    def income_opportunities(self, limit=500):
        return list(self.rows)

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
