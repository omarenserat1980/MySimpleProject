from __future__ import annotations

import unittest

from brain_v12.brain.software_capability_candidate_catalog import build_catalog


class SoftwareCapabilityCandidateCatalogTests(unittest.TestCase):
    def setUp(self):
        self.inventory = {"schema": "inventory-test/v1", "safety": {"network_probed": False}}
        self.report = {
            "schema": "audit-test/v1",
            "capabilities": [
                {"capability_id": "local_python_runtime", "description": "Python", "status": "OBSERVED_NOT_YET_RUNTIME_VERIFIED", "observed_present": True, "evidence_level": "LOCAL_RUNTIME_PRESENT"},
                {"capability_id": "media_transcoding", "description": "Media", "status": "MISSING_LOCAL_REQUIREMENT", "observed_present": False, "evidence_level": "TOOLS_MISSING"},
                {"capability_id": "remote_device_execution", "description": "Remote", "status": "BLOCKED_NEEDS_EXTERNAL_EVIDENCE", "observed_present": False, "evidence_level": "LIVE_DEVICE_EVIDENCE_REQUIRED"},
            ],
        }

    def test_discovered_candidate_never_becomes_online_executor(self):
        catalog = build_catalog(self.inventory, self.report)
        python_node = next(node for node in catalog["nodes"] if node["node_id"] == "local_python_runtime")
        self.assertEqual(python_node["candidate_state"], "DISCOVERED_NOT_RUNTIME_VERIFIED")
        self.assertEqual(python_node["executor_state"], "NOT_REGISTERED")
        self.assertFalse(python_node["registration_allowed_by_this_report"])
        self.assertFalse(catalog["executor_online_claimed"])

    def test_missing_capability_is_reported_as_gap(self):
        catalog = build_catalog(self.inventory, self.report)
        media_node = next(node for node in catalog["nodes"] if node["node_id"] == "media_transcoding")
        self.assertEqual(media_node["candidate_state"], "GAP")

    def test_remote_execution_stays_blocked_without_live_evidence(self):
        catalog = build_catalog(self.inventory, self.report)
        remote_node = next(node for node in catalog["nodes"] if node["node_id"] == "remote_device_execution")
        self.assertEqual(remote_node["candidate_state"], "BLOCKED_NEEDS_EVIDENCE")
        self.assertIn("fresh heartbeat", remote_node["promotion_requirements"])

    def test_catalog_does_not_mutate_or_import_registry(self):
        catalog = build_catalog(self.inventory, self.report)
        self.assertFalse(catalog["capability_registry_mutated"])
        self.assertFalse(catalog["capability_registry_imported"])
        self.assertEqual(catalog["mode"], "REVIEW_ONLY_NO_REGISTRATION")

    def test_unrecognized_status_is_not_promoted(self):
        report = {"capabilities": [{"capability_id": "future_node", "status": "UNKNOWN", "observed_present": False}]}
        catalog = build_catalog(self.inventory, report)
        node = catalog["nodes"][0]
        self.assertEqual(node["candidate_state"], "UNCLASSIFIED_REQUIRES_REVIEW")
        self.assertEqual(node["executor_state"], "NOT_REGISTERED")


if __name__ == "__main__":
    unittest.main()
