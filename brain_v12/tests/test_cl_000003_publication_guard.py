import unittest
from brain_v12.business.cl_000003_publication_guard import require_master_release
from brain_v12.business.cl_000003_master_release_gate import REQUIRED

class PublicationGuardTests(unittest.TestCase):
    def good(self):
        return {
            "film_id":"F1","film_version":"v1","production_run":"R1",
            **{k:{"passed":True,"evidence_ref":f"e/{k}","evidence_sha256":"a"*64} for k in REQUIRED}
        }

    def test_no_evidence_blocks(self):
        self.assertFalse(require_master_release(None)["authorized"])

    def test_wrong_master_status_is_recomputed(self):
        e=self.good()
        e["cinematic"]["passed"]=False
        r=require_master_release(e)
        self.assertFalse(r["authorized"])

    def test_missing_identity_blocks(self):
        e=self.good(); e.pop("film_id")
        r=require_master_release(e)
        self.assertFalse(r["authorized"])

    def test_valid_master_release_allows_gate(self):
        r=require_master_release(self.good())
        self.assertTrue(r["authorized"])
        self.assertEqual(r["status"], "MASTER_RELEASE_AUTHORIZED")

if __name__ == "__main__":
    unittest.main()
