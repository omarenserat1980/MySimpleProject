import hashlib
import unittest
from brain_v12.business.cl_000003_master_release_gate import REQUIRED, decide
from brain_v12.business.cl_000003_publication_guard import require_master_release
class DeepIntegrityLoopTests(unittest.TestCase):
    def good(self,i=1):
        artifact=hashlib.sha256(f"artifact-{i}".encode()).hexdigest()
        return {"artifact_sha256":artifact,"film_id":f"F{i}","film_version":"v1","production_run":f"R{i}",
                **{k:{"passed":True,"evidence_ref":f"F{i}/v1/R{i}/{k}/qc.json","evidence_sha256":hashlib.sha256(f"{i}-{k}".encode()).hexdigest(),"reviewed_artifact_sha256":artifact} for k in REQUIRED}}
    def test_reused_evidence_from_other_film_is_rejected(self):
        e=self.good(1); e["cinematic"]["evidence_ref"]="F2/v1/R2/cinematic/qc.json"; self.assertFalse(decide(e)["publish_authorized"])
    def test_missing_artifact_hash_is_rejected(self):
        e=self.good(); e.pop("artifact_sha256"); self.assertFalse(decide(e)["publish_authorized"])
    def test_changed_artifact_hash_is_rejected(self):
        e=self.good(); e["artifact_sha256"]="b"*64; self.assertFalse(require_master_release(e)["authorized"])
    def test_gate_reviewed_hash_mismatch_is_rejected(self):
        e=self.good(); e["cinematic"]["reviewed_artifact_sha256"]="c"*64; self.assertFalse(decide(e)["publish_authorized"])
    def test_valid_bound_evidence_is_authorized(self): self.assertTrue(require_master_release(self.good())["authorized"])
if __name__=="__main__": unittest.main()
