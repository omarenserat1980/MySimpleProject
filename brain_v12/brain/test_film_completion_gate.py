import json,tempfile,unittest
from pathlib import Path
from .film_completion_gate import FilmCompletionGate

class FilmCompletionGateTests(unittest.TestCase):
    def test_missing_artifact_is_incomplete(self):
        with tempfile.TemporaryDirectory() as d:
            r=FilmCompletionGate(d).check()
            self.assertFalse(r["completed"])
            self.assertIn("FINAL_MP4_MISSING",r["reasons"])
    def test_manifest_without_master_qc_is_not_complete(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/"manifest.json").write_text(json.dumps({"status":"VERIFIED_COMPLETED","parts":1}),encoding="utf-8"); (p/"VERIFIED_COMPLETED").write_text("ok",encoding="utf-8")
            r=FilmCompletionGate(p).check()
            self.assertFalse(r["completed"])
            self.assertIn("FINAL_MP4_MISSING",r["reasons"])

if __name__=="__main__": unittest.main()
