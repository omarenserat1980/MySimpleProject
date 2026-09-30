import unittest,tempfile
from brain_v12.brain.economic_cycle import EconomicCycle
from brain_v12.brain.economic_ledger import EconomicLedger
from brain_v12.brain.payment_adapters import BaseUSDCAdapter

class Tests(unittest.TestCase):
    def test_receipt_only_creates_verified_revenue(self):
        with tempfile.TemporaryDirectory() as d:
            l=EconomicLedger(d+"/ledger.jsonl"); c=EconomicCycle(ledger=l)
            r=c.verify_and_record("job-1",{"tx_hash":"0xabc","network":"base-mainnet","amount":"0.10","currency":"USDC"},BaseUSDCAdapter())
            self.assertEqual(r["state"],"VERIFIED_RECEIVED")
            self.assertEqual(l.verified_total("USDC"),0.1)
    def test_fake_receipt_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            l=EconomicLedger(d+"/ledger.jsonl"); c=EconomicCycle(ledger=l)
            r=c.verify_and_record("job-1",{"amount":"10","currency":"USDC"},BaseUSDCAdapter())
            self.assertEqual(r["status"],"REJECTED")
if __name__=="__main__": unittest.main()
