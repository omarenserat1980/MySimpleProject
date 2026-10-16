from __future__ import annotations

import unittest
from datetime import datetime, timezone, timedelta

from brain_v12.brain.software_capability_candidate_catalog import build_catalog
from brain_v12.brain.software_capability_promotion_gate import evaluate_promotion


NOW = datetime(2026, 10, 16, 9, 0, tzinfo=timezone.utc)


def catalog_fixture():
    inventory = {"schema": "inventory-test/v1"}
    report = {
        "schema": "audit-test/v1",
        "capabilities": [{
            "capability_id": "local_python_runtime",
            "description": "Python",
            "status": "OBSERVED_NOT_YET_RUNTIME_VERIFIED",
            "observed_present": True,
            "evidence_level": "LOCAL_RUNTIME_PRESENT",
        }],
    }
    return build_catalog(inventory, report)


def valid_evidence():
    catalog = catalog_fixture()
    node = catalog["nodes"][0]
    stamp = (NOW - timedelta(minutes=5)).isoformat()
    return {
        "schema": "brain-capability-evidence/v1",
        "capability_id": "local_python_runtime",
        "checks": [
            {"requirement": requirement, "result": "PASS",
             "evidence_ref": f"evidence://test/{i}", "observed_at": stamp}
            for i, requirement in enumerate(node["promotion_requirements"])
        ],
    }


class SoftwareCapabilityPromotionGateTests(unittest.TestCase):
    def test_complete_fresh_evidence_only_qualifies_for_human_review(self):
        result = evaluate_promotion("local_python_runtime", valid_evidence(),
                                    catalog_fixture(), now=NOW)
        self.assertTrue(result["eligible_for_human_review"])
        self.assertEqual(result["decision"], "ELIGIBLE_FOR_HUMAN_REVIEW")
        self.assertFalse(result["automatic_registration_allowed"])
        self.assertEqual(result["executor_state"], "NOT_REGISTERED")
        self.assertFalse(result["capability_registry_mutated"])

    def test_missing_requirement_blocks(self):
        evidence = valid_evidence()
        evidence["checks"].pop()
        result = evaluate_promotion("local_python_runtime", evidence,
                                    catalog_fixture(), now=NOW)
        self.assertFalse(result["eligible_for_human_review"])
        self.assertTrue(any("REQUIRED_EVIDENCE_MISSING" in reason for reason in result["reasons"]))

    def test_stale_evidence_blocks(self):
        evidence = valid_evidence()
        for check in evidence["checks"]:
            check["observed_at"] = (NOW - timedelta(hours=25)).isoformat()
        result = evaluate_promotion("local_python_runtime", evidence,
                                    catalog_fixture(), now=NOW)
        self.assertFalse(result["eligible_for_human_review"])
        self.assertTrue(any("EVIDENCE_TOO_OLD" in reason for reason in result["reasons"]))

    def test_missing_evidence_reference_blocks(self):
        evidence = valid_evidence()
        evidence["checks"][0]["evidence_ref"] = " "
        result = evaluate_promotion("local_python_runtime", evidence,
                                    catalog_fixture(), now=NOW)
        self.assertFalse(result["eligible_for_human_review"])
        self.assertTrue(any("EVIDENCE_REFERENCE_MISSING" in reason for reason in result["reasons"]))

    def test_future_timestamp_blocks(self):
        evidence = valid_evidence()
        evidence["checks"][0]["observed_at"] = (NOW + timedelta(minutes=1)).isoformat()
        result = evaluate_promotion("local_python_runtime", evidence,
                                    catalog_fixture(), now=NOW)
        self.assertFalse(result["eligible_for_human_review"])
        self.assertTrue(any("OBSERVATION_FROM_FUTURE" in reason for reason in result["reasons"]))

    def test_capability_id_mismatch_blocks(self):
        evidence = valid_evidence()
        evidence["capability_id"] = "physical_mining"
        result = evaluate_promotion("local_python_runtime", evidence,
                                    catalog_fixture(), now=NOW)
        self.assertFalse(result["eligible_for_human_review"])
        self.assertIn("CAPABILITY_ID_MISMATCH", result["reasons"])

    def test_unknown_capability_never_qualifies(self):
        result = evaluate_promotion("not-in-catalog", valid_evidence(),
                                    catalog_fixture(), now=NOW)
        self.assertFalse(result["eligible_for_human_review"])
        self.assertIn("CAPABILITY_NOT_IN_CATALOG", result["reasons"])

    def test_catalog_gap_cannot_be_promoted(self):
        catalog = build_catalog(
            {"schema": "inventory-test/v1"},
            {"capabilities": [{
                "capability_id": "media_transcoding", "status": "MISSING_LOCAL_REQUIREMENT",
                "observed_present": False, "promotion_requirements": []
            }]},
        )
        result = evaluate_promotion("media_transcoding", {
            "schema": "brain-capability-evidence/v1",
            "capability_id": "media_transcoding",
            "checks": [],
        }, catalog, now=NOW)
        self.assertFalse(result["eligible_for_human_review"])
        self.assertIn("CATALOG_STATE_REQUIRES_REVIEW", result["reasons"])

    def test_invalid_schema_blocks(self):
        evidence = valid_evidence()
        evidence["schema"] = "unknown/v1"
        result = evaluate_promotion("local_python_runtime", evidence,
                                    catalog_fixture(), now=NOW)
        self.assertFalse(result["eligible_for_human_review"])
        self.assertIn("INVALID_EVIDENCE_SCHEMA", result["reasons"])

    def test_non_object_evidence_blocks_without_exception(self):
        result = evaluate_promotion("local_python_runtime", [],
                                    catalog_fixture(), now=NOW)
        self.assertFalse(result["eligible_for_human_review"])
        self.assertIn("INVALID_EVIDENCE_DOCUMENT", result["reasons"])


if __name__ == "__main__":
    unittest.main()
