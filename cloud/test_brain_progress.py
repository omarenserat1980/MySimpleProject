import unittest, tempfile, json
from pathlib import Path
import cloud.brain_progress as bp

class BrainProgressTests(unittest.TestCase):
    def test_only_verified_adds_evidence_progress(self):
        with tempfile.TemporaryDirectory() as d:
            old=bp.LEDGER
            bp.LEDGER=Path(d)/"progress.json"
            out=bp.update_progress({"status":"VERIFIED","evidence":["a","b"]})
            self.assertEqual(out["verified_results"],1)
            self.assertEqual(out["evidence_items"],2)
            bp.LEDGER=old

if __name__=="__main__":
    unittest.main()
