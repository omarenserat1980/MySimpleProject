import hashlib
import json
import unittest
from unittest.mock import patch

from brain_v12.brain import device_preflight


class DevicePreflightTests(unittest.TestCase):
    def test_report_is_read_only_and_fails_closed(self):
        report = device_preflight.build_preflight_report("redmi")
        self.assertEqual(report["device_alias"], "redmi")
        self.assertFalse(report["identity_verified"])
        self.assertFalse(report["attestation_verified"])
        self.assertFalse(report["execution_eligible"])
        self.assertFalse(report["network_probed"])
        self.assertFalse(report["secrets_read"])
        self.assertIn("logical_cpu_count", report["resources"])
        self.assertEqual(set(report["tools"]), set(device_preflight.TOOL_CANDIDATES))

    def test_unknown_alias_is_rejected(self):
        with self.assertRaises(ValueError):
            device_preflight.build_preflight_report("redmi;run-command")

    def test_digest_matches_canonical_report_without_digest(self):
        report = device_preflight.build_preflight_report("arkan")
        digest = report.pop("report_sha256")
        canonical = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        self.assertEqual(digest, hashlib.sha256(canonical.encode("utf-8")).hexdigest())

    def test_environment_secrets_are_not_serialized(self):
        with patch.dict("os.environ", {"BRAIN_CONTROL_KEY": "do-not-export-this"}):
            report = device_preflight.build_preflight_report("realme")
        rendered = json.dumps(report)
        self.assertNotIn("do-not-export-this", rendered)
        self.assertNotIn("BRAIN_CONTROL_KEY", rendered)

    def test_tool_detection_is_bounded_to_fixed_candidates(self):
        with patch.object(device_preflight.shutil, "which", return_value=None) as which:
            report = device_preflight.build_preflight_report()
        self.assertTrue(all(value is False for value in report["tools"].values()))
        self.assertLessEqual(which.call_count, sum(len(v) for v in device_preflight.TOOL_CANDIDATES.values()))


if __name__ == "__main__":
    unittest.main()
