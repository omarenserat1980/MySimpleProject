import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "tools" / "asic_physical_evidence_gate.py"
spec = importlib.util.spec_from_file_location("asic_gate", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class GateTests(unittest.TestCase):
    def test_empty_manifest_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "manifest.json"
            p.write_text(json.dumps({"project":"test","stages":{},"artifacts":{}}))
            result = module.audit(p)
            self.assertEqual(result["overall_status"], "EVIDENCE_INCOMPLETE")
            self.assertFalse(result["fabrication_claim_allowed"])

    def test_rtl_only_never_means_fabricated(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifact = root / "rtl.log"
            artifact.write_text("ASIC_RTL_TB_PASS\n")
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            manifest = {
                "project":"test",
                "stages":{"rtl_simulation":{"test_log":"rtl_log"}},
                "artifacts":{"rtl_log":{"path":"rtl.log","sha256":digest}}
            }
            p = root / "manifest.json"
            p.write_text(json.dumps(manifest))
            result = module.audit(p)
            self.assertEqual(result["overall_status"], "RTL_SIMULATION_ONLY")
            self.assertFalse(result["fabrication_claim_allowed"])

if __name__ == "__main__":
    unittest.main()
