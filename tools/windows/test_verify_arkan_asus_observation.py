#!/usr/bin/env python3
"""Regression tests for the fail-closed ASUS observation report verifier."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERIFIER = ROOT / "tools" / "windows" / "verify_arkan_asus_observation.py"


def make_report(observed_at=None):
    payload = {
        "schema": "brain.arkan-asus-golden-loop-observation.v1",
        "mission": "ARKAN_ASUS_COMPUTER_BUILD",
        "stage": "OBSERVE",
        "observed_at_utc": (observed_at or datetime.now(timezone.utc)).isoformat(),
        "host": {
            "computer_name": "TEST-HOST",
            "manufacturer": "ASUS",
            "model": "TEST-MODEL",
        },
    }
    canonical = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    return {
        "payload_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "payload_canonical_json": canonical,
        "payload": payload,
    }


class ObservationVerifierTests(unittest.TestCase):
    def run_verifier(self, report):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "observation.json"
            path.write_text(json.dumps(report), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(VERIFIER), str(path)],
                text=True,
                capture_output=True,
                check=False,
            )

    def test_valid_fresh_report_passes_integrity_but_requires_manual_identity_review(self):
        result = self.run_verifier(make_report())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("REPORT_INTEGRITY=PASS", result.stdout)
        self.assertIn("PHYSICAL_ASUS_IDENTITY=MANUAL_REVIEW_REQUIRED", result.stdout)
        self.assertIn("MISSION_STATE=OPEN_NOT_CLOSED", result.stdout)

    def test_modified_canonical_json_fails_hash(self):
        report = make_report()
        report["payload_canonical_json"] += " "
        result = self.run_verifier(report)
        self.assertEqual(result.returncode, 2)
        self.assertIn("REPORT_INTEGRITY=FAIL", result.stderr)

    def test_payload_mismatch_fails(self):
        report = make_report()
        report["payload"]["host"]["model"] = "ALTERED"
        result = self.run_verifier(report)
        self.assertEqual(result.returncode, 2)
        self.assertIn("differs from payload_canonical_json", result.stderr)

    def test_stale_report_fails(self):
        old = datetime.now(timezone.utc) - timedelta(hours=30)
        result = self.run_verifier(make_report(old))
        self.assertEqual(result.returncode, 2)
        self.assertIn("stale report", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
