import tempfile,unittest
from brain_v12.brain.authorization_gate import AuthorizationGate
from brain_v12.brain.economic_ledger import EconomicLedger
from brain_v12.brain.payout_planner import PayoutPlanner

class Tests(unittest.TestCase):
    def test_money_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            g=AuthorizationGate(d+"/events.jsonl")
            self.assertEqual(g.decide("move_money")["decision"],"HUMAN_REVIEW")
    def test_payout_cannot_exceed_verified_revenue(self):
        with tempfile.TemporaryDirectory() as d:
            l=EconomicLedger(d+"/ledger.jsonl"); l.record("x","VERIFIED_RECEIVED",5,"JOD",{"receipt":"r"})
            p=PayoutPlanner(l,AuthorizationGate(d+"/auth.jsonl"))
            self.assertEqual(p.plan_to_owner(6)["status"],"DENIED")
            self.assertEqual(p.plan_to_owner(5)["status"],"AWAITING_OWNER_APPROVAL")
    def test_approved_payout_is_only_ready(self):
        with tempfile.TemporaryDirectory() as d:
            l=EconomicLedger(d+"/ledger.jsonl"); l.record("x","VERIFIED_RECEIVED",5,"JOD",{"receipt":"r"})
            p=PayoutPlanner(l,AuthorizationGate(d+"/auth.jsonl"))
            r=p.plan_to_owner(5,"JOD","orange_money",True,"approval-1")
            self.assertEqual(r["status"],"READY_FOR_PAYMENT_ADAPTER")

if __name__=="__main__":unittest.main()
