import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from brain_v12.tools.asic_identity_evidence_v2 import build_report, load_record

class AsicIdentityEvidenceTests(unittest.TestCase):
    def test_no_record_is_unverified(self):
        report = build_report([], None)
        self.assertEqual(report["status"], "PHYSICAL_IDENTITY_UNVERIFIED")
        self.assertFalse(report["serial_match"])

    def test_matching_serial_requires_review_not_verified(self):
        record = {"manufacturer":"Example", "model":"ASIC-X", "serial":"SN-12345",
                  "evidence_uri":"asset://record/1", "verified_by":"reviewer"}
        report = build_report([{"serial":"SN-12345"}], record)
        self.assertTrue(report["serial_match"])
        self.assertEqual(report["status"], "RECORD_SERIAL_MATCHED_REQUIRES_INDEPENDENT_REVIEW")
        self.assertNotEqual(report["status"], "PHYSICAL_IDENTITY_VERIFIED")

    def test_nonmatching_serial_is_unverified(self):
        record = {"manufacturer":"Example", "model":"ASIC-X", "serial":"SN-12345",
                  "evidence_uri":"asset://record/1", "verified_by":"reviewer"}
        self.assertEqual(build_report([{"serial":"OTHER"}], record)["status"], "PHYSICAL_IDENTITY_UNVERIFIED")

    def test_invalid_record_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "record.json"
            p.write_text(json.dumps({"serial":"x"}), encoding="utf-8")
            self.assertIn("record_error", load_record(str(p)))

if __name__ == "__main__":
    unittest.main()
