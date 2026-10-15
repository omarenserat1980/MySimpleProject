"""Tests for the fail-closed mining evidence bundle integrity checker."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.mining_evidence_bundle import (
    REQUIRED_ARTIFACTS, sha256_file, verify_bundle, write_example_manifest,
)


class EvidenceBundleTests(unittest.TestCase):
    def test_synthetic_bundle_only_passes_integrity_not_mining(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = write_example_manifest(temp)
            result = verify_bundle(manifest)
        self.assertTrue(result["integrity_ok"])
        self.assertFalse(result["independently_verified"])
        self.assertFalse(result["real_mining_verified"])
        self.assertFalse(result["revenue_verified"])
        self.assertEqual(result["state"], "INTEGRITY_CHECK_PASSED_NOT_INDEPENDENTLY_VERIFIED")

    def test_tampered_artifact_is_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = write_example_manifest(temp)
            data = json.loads(manifest.read_text())
            artifact = Path(temp) / data["artifacts"][REQUIRED_ARTIFACTS[0]]["path"]
            artifact.write_text("tampered\n")
            result = verify_bundle(manifest)
        self.assertFalse(result["integrity_ok"])
        self.assertIn(REQUIRED_ARTIFACTS[0], result["invalid_artifacts"])
        self.assertFalse(result["real_mining_verified"])

    def test_missing_manifest_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            result = verify_bundle(Path(temp) / "absent.json")
        self.assertEqual(result["state"], "BLOCKED")
        self.assertFalse(result["integrity_ok"])

    def test_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            outside = base.parent / "outside-brain-evidence.txt"
            outside.write_text("not in bundle")
            manifest = base / "manifest.json"
            manifest.write_text(json.dumps({"artifacts": {
                "host_attestation": {"path": "../outside-brain-evidence.txt", "sha256": sha256_file(outside)}
            }}))
            result = verify_bundle(manifest)
            self.assertIn("host_attestation", result["invalid_artifacts"])
            self.assertFalse(result["integrity_ok"])
            outside.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
