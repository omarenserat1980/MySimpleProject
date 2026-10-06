import unittest
from brain_v12.business.cl_000003_master_release_gate import decide, REQUIRED
from brain_v12.business.cl_000003_publication_guard import require_master_release

class TenLayerReleaseAttackTests(unittest.TestCase):
    def good(self):
        return {
            "film_id":"F1","film_version":"v1","production_run":"R1",
            **{k:{"passed":True,"evidence_ref":f"e/{k}","evidence_sha256":"a"*64} for k in REQUIRED}
        }

    def assert_blocked(self, evidence):
        self.assertFalse(decide(evidence)["publish_authorized"])

    def test_01_empty(self): self.assert_blocked({})
    def test_02_publication_recomputes_gates(self):
        e=self.good()
        self.assertTrue(require_master_release(e)["authorized"])
        e["cinematic"]["passed"]=False
        self.assertFalse(require_master_release(e)["authorized"])
    def test_03_missing_film_id(self):
        e=self.good(); e.pop("film_id"); self.assert_blocked(e)
    def test_04_missing_version(self):
        e=self.good(); e.pop("film_version"); self.assert_blocked(e)
    def test_05_missing_run(self):
        e=self.good(); e.pop("production_run"); self.assert_blocked(e)
    def test_06_cinematic_false(self):
        e=self.good(); e["cinematic"]["passed"]=False; self.assert_blocked(e)
    def test_07_rights_hash_missing(self):
        e=self.good(); e["rights"].pop("evidence_sha256"); self.assert_blocked(e)
    def test_08_bad_hash_length(self):
        e=self.good(); e["legal_policy"]["evidence_sha256"]="bad"; self.assert_blocked(e)
    def test_09_forged_publish_status_is_ignored(self):
        e=self.good(); e["status"]="MASTER_RELEASE_PASS"; e["publish_authorized"]=True
        e["rights"]["passed"]=False
        self.assertFalse(require_master_release(e)["authorized"])
    def test_10_forged_gate_decision_is_recomputed(self):
        e=self.good(); e["status"]="MASTER_RELEASE_PASS"; e["publish_authorized"]=True
        e["legal_policy"]["passed"]=False
        self.assertFalse(require_master_release(e)["authorized"])

if __name__=="__main__": unittest.main()
