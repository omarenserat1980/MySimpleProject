import unittest
from dataclasses import replace

from brain_v12.brain.self_engineering import (
    Evidence, EvidenceKind, RunState, SelfEngineeringEngine,
)


class SelfEngineeringEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = SelfEngineeringEngine()
        self.run = self.engine.start("Improve self-verification")
        self.engine.record_inspection(
            self.run, source="test-fixture",
            findings=["existing test coverage", "runtime probe required"],
        )

    def test_run_starts_with_inspection_and_creates_plan(self):
        self.assertEqual(self.run.state, RunState.PLANNED)
        self.assertTrue(self.run.plan)
        self.assertTrue(self.run.claims()["source_inspected"])

    def test_empty_inspection_is_not_claimed_as_passed(self):
        run = self.engine.start("Inspect missing source")
        self.engine.record_inspection(run, source="test-fixture", findings=[])
        self.assertEqual(run.state, RunState.BLOCKED)
        self.assertFalse(run.claims()["source_inspected"])
        self.assertIn("SOURCE_INSPECTION_INCOMPLETE", run.blockers)

    def test_blank_inspection_source_is_not_accepted(self):
        run = self.engine.start("Inspect source")
        self.engine.record_inspection(run, source="  ", findings=["some finding"])
        self.assertFalse(run.claims()["source_inspected"])
        self.assertEqual(run.state, RunState.BLOCKED)

    def test_inspection_details_cannot_override_validated_findings(self):
        run = self.engine.start("Inspect source")
        self.engine.record_inspection(
            run, source="test-fixture", findings=["verified finding"],
            details={"findings": []},
        )
        self.assertTrue(run.claims()["source_inspected"])
        evidence = run.evidence[-1]
        self.assertEqual(evidence.details["findings"], ["verified finding"])
        self.assertTrue(evidence.verify_digest())

    def test_cannot_execute_without_scoped_approval(self):
        self.engine.begin_execution(self.run)
        self.assertEqual(self.run.state, RunState.BLOCKED)
        self.assertIn("SOURCE_MUTATION_NOT_AUTHORIZED", self.run.blockers)

    def test_approval_requires_scope(self):
        with self.assertRaisesRegex(ValueError, "AUTHORIZATION_SCOPE_REQUIRED"):
            self.engine.authorize_changes(self.run, approved=True)

    def test_tests_are_required_before_verified(self):
        self.engine.finalize(self.run)
        self.assertEqual(self.run.state, RunState.BLOCKED)
        self.assertIn("PASSING_TEST_EVIDENCE_REQUIRED", self.run.blockers)

    def test_runtime_required_is_not_implied_by_tests(self):
        self.engine.record_test_result(self.run, passed=True, source="ci")
        self.engine.finalize(self.run, runtime_required=True)
        self.assertEqual(self.run.state, RunState.BLOCKED)
        self.assertIn("LIVE_RUNTIME_EVIDENCE_REQUIRED", self.run.blockers)

    def test_runtime_probe_plus_passing_tests_can_verify_run(self):
        self.engine.record_test_result(self.run, passed=True, source="live-ci")
        self.engine.record_runtime_probe(self.run, passed=True, source="live-api")
        self.engine.finalize(self.run, runtime_required=True)
        self.assertEqual(self.run.state, RunState.VERIFIED)
        self.assertTrue(self.run.claims()["runtime_verified"])

    def test_failed_tests_cannot_be_overridden_by_runtime_probe(self):
        self.engine.record_test_result(self.run, passed=False, source="ci")
        self.engine.record_runtime_probe(self.run, passed=True, source="live-api")
        self.engine.finalize(self.run)
        self.assertEqual(self.run.state, RunState.FAILED)

    def test_evidence_digest_is_verified_on_add(self):
        evidence = Evidence.create(
            EvidenceKind.TEST_RESULT, "tests", "passed", "ci", {"count": 3}
        )
        self.assertTrue(evidence.verify_digest())
        self.run.add_evidence(evidence)
        self.assertEqual(self.run.report()["evidence_count"], 2)

    def test_tampered_evidence_is_rejected(self):
        evidence = Evidence.create(
            EvidenceKind.TEST_RESULT, "tests", "passed", "ci", {"count": 3}
        )
        tampered = replace(evidence, claim="changed after digest")
        with self.assertRaisesRegex(ValueError, "EVIDENCE_DIGEST_MISMATCH"):
            self.run.add_evidence(tampered)

    def test_claims_ignore_evidence_tampered_after_insertion(self):
        evidence = Evidence.create(
            EvidenceKind.TEST_RESULT, "tests", "passed", "ci", {"count": 3}
        )
        self.run.add_evidence(evidence)
        self.run.evidence[-1] = replace(evidence, outcome="failed")
        self.assertFalse(self.run.claims()["tests_passed"])

    def test_empty_goal_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "GOAL_REQUIRED"):
            self.engine.start("  ")


if __name__ == "__main__":
    unittest.main()
