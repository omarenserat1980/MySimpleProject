"""Tests for the evidence-aware capability gap audit."""
import unittest

from brain_v12.brain.software_capability_gap_audit import audit


def sample_inventory():
    return {
        "schema": "brain-software-node-inventory/v1",
        "host": {"python_executable": "C:/Python/python.exe"},
        "python_modules": [],
        "executables": [
            {"name": "ffmpeg", "available": True, "path": "C:/ffmpeg.exe"},
            {"name": "ffprobe", "available": True, "path": "C:/ffprobe.exe"},
        ],
        "brain_components": [
            {"path": "brain_v12/brain/tool_foundry.py", "present": True},
        ],
    }


class SoftwareCapabilityGapAuditTests(unittest.TestCase):
    def test_local_presence_is_not_marked_runtime_verified(self):
        report = audit(sample_inventory())
        self.assertEqual(report["mode"], "PLAN_ONLY_NO_REGISTRATION")
        self.assertFalse(report["capability_registry_mutated"])
        self.assertFalse(report["generated_code_executed"])
        self.assertFalse(report["network_probed"])
        media = next(x for x in report["capabilities"] if x["capability_id"] == "media_transcoding")
        self.assertTrue(media["observed_present"])
        self.assertEqual(media["status"], "OBSERVED_NOT_YET_RUNTIME_VERIFIED")

    def test_remote_devices_and_mining_require_external_evidence(self):
        report = audit(sample_inventory())
        remote = next(x for x in report["capabilities"] if x["capability_id"] == "remote_device_execution")
        mining = next(x for x in report["capabilities"] if x["capability_id"] == "physical_mining")
        self.assertEqual(remote["status"], "BLOCKED_NEEDS_EXTERNAL_EVIDENCE")
        self.assertEqual(mining["status"], "BLOCKED_NEEDS_EXTERNAL_EVIDENCE")
        self.assertFalse(mining["observed_present"])
        self.assertFalse(report["mining_enabled"])

    def test_missing_local_tools_are_reported_as_gaps(self):
        report = audit(sample_inventory())
        android = next(x for x in report["capabilities"] if x["capability_id"] == "android_bridge")
        rtl = next(x for x in report["capabilities"] if x["capability_id"] == "rtl_simulation")
        self.assertEqual(android["status"], "MISSING_LOCAL_REQUIREMENT")
        self.assertEqual(rtl["status"], "MISSING_LOCAL_REQUIREMENT")
        self.assertGreater(report["gap_count"], 0)

    def test_missing_tool_foundry_source_is_not_assumed(self):
        inventory = sample_inventory()
        inventory["brain_components"] = []
        report = audit(inventory)
        foundry = next(x for x in report["capabilities"] if x["capability_id"] == "brain_tool_foundry")
        self.assertEqual(foundry["status"], "MISSING_LOCAL_REQUIREMENT")


if __name__ == "__main__":
    unittest.main()
