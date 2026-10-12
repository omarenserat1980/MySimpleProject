"""Unit tests for the read-only Windows Cloud progress gate."""
import unittest
from pathlib import Path

from brain_v12.tools.windows_cloud_progress_gate import find_repo_root, summarize


class WindowsCloudProgressGateTests(unittest.TestCase):
    def test_missing_api_is_reported_as_actionable_blocker(self):
        report = summarize("http://127.0.0.1:8012", {
            key: {"reachable": False, "http_status": None}
            for key in ("provider", "enrollment", "guest", "datacenter")
        }, None)
        codes = {item["code"] for item in report["blockers"]}
        self.assertIn("REPOSITORY_NOT_FOUND", codes)
        self.assertIn("BRAIN_API_UNREACHABLE", codes)
        self.assertFalse(report["windows_boot_proven"])

    def test_missing_enrollment_fields_are_reported_without_values(self):
        results = {
            "provider": {"reachable": True, "http_status": 200,
                         "data": {"ready": False, "provider_readiness": {
                             "ready": False, "reason": "CLOUD_WINDOWS_PROVIDER_NOT_CONFIGURED"}}},
            "enrollment": {"reachable": True, "http_status": 200,
                           "data": {"ready": False, "missing": ["fabric_url", "enrollment_token"]}},
            "guest": {"reachable": True, "http_status": 200,
                      "data": {"verified": False, "status": "WINDOWS_CLOUD_UNAVAILABLE"}},
            "datacenter": {"reachable": True, "http_status": 200,
                            "data": {"status": "EMPTY", "windows_vms": []}},
        }
        report = summarize("http://localhost:8012", results, Path("/repo"))
        codes = {item["code"] for item in report["blockers"]}
        self.assertIn("CLOUD_WINDOWS_PROVIDER_NOT_CONFIGURED", codes)
        self.assertIn("WINDOWS_GUEST_ENROLLMENT_NOT_READY", codes)
        self.assertIn("DATACENTER_HAS_NO_WINDOWS_VM", codes)
        self.assertIn("REAL_WINDOWS_BOOT_EVIDENCE_NOT_CHECKED", codes)
        serialized = str(report)
        self.assertNotIn("enrollment-secret-value", serialized)

    def test_http_200_does_not_mean_guest_verified(self):
        results = {
            "provider": {"reachable": True, "http_status": 200, "data": {"ready": False}},
            "enrollment": {"reachable": True, "http_status": 200, "data": {"ready": True, "missing": []}},
            "guest": {"reachable": True, "http_status": 200,
                      "data": {"verified": False, "status": "WINDOWS_CLOUD_UNAVAILABLE"}},
            "datacenter": {"reachable": True, "http_status": 200,
                            "data": {"status": "EMPTY", "windows_vms": []}},
        }
        report = summarize("http://localhost:8012", results, Path("/repo"))
        self.assertFalse(report["windows_boot_proven"])
        self.assertTrue(any(item["code"] == "WINDOWS_CLOUD_UNAVAILABLE"
                            for item in report["blockers"]))


if __name__ == "__main__":
    unittest.main()
