import tempfile, unittest
from brain_v12.brain.economic_ledger import EconomicLedger

class EconomicLedgerTests(unittest.TestCase):
    def test_expected_is_not_verified(self):
        with tempfile.TemporaryDirectory() as d:
            l=EconomicLedger(d+"/ledger.jsonl")
            l.record("x","EXPECTED",10,"JOD")
            l.record("x","EARNED",10,"JOD")
            self.assertEqual(l.verified_total("JOD"),0)

    def test_verified_requires_receipt_record(self):
        with tempfile.TemporaryDirectory() as d:
            l=EconomicLedger(d+"/ledger.jsonl")
            l.record("x","VERIFIED_RECEIVED",2.5,"USDC",evidence={"tx":"abc"})
            self.assertEqual(l.verified_total("USDC"),2.5)

if __name__ == "__main__":
    unittest.main()
