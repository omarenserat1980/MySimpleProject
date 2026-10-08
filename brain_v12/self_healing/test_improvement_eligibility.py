import unittest
from pathlib import Path


class ImprovementEligibilityContractTests(unittest.TestCase):
    def test_generator_requires_explicit_supported_candidate(self):
        source = Path("brain_v12/self_healing/review_loop.py").read_text(encoding="utf-8")
        self.assertIn("from .generator_registry import supported_candidates", source)
        self.assertIn("eligible_candidates = supported_candidates(improvement.get(\"candidates\", []))", source)
        self.assertIn("bool(eligible_candidates)", source)
        self.assertIn('mode == "GENERATOR_ELIGIBLE"', source)
        self.assertIn("generator_configured", source)


    def test_discovery_detects_sys_executable_package_invocation(self):
        from brain_v12.self_healing.improvement_engine import discover
        candidates = discover()
        matches = [c for c in candidates if c.get("id") == "package-invocation-consistency"]
        self.assertTrue(matches)
        self.assertTrue(any(c.get("file") == "brain_v12/self_healing/verification_gate.py" for c in matches))

    def test_repair_recurrence_guard_is_present(self):
        source = Path("brain_v12/self_healing/review_loop.py").read_text(encoding="utf-8")
        self.assertIn("repair_failure_identity", source)
        self.assertIn("repair_recurrence_blocked", source)
        self.assertIn("REPAIR_BLOCKED_RECURRING_FAILURE", source)
        self.assertIn("same_failure_on_same_baseline_already_attempted", source)

    def test_generator_is_not_called_inside_ineligible_branch(self):
        source = Path("brain_v12/self_healing/review_loop.py").read_text(encoding="utf-8")
        not_applied = source.index('entry["proactive_improvement"] = {')
        repair_call = source.index("improved, improvement_details = repair(args.timeout)")
        eligible = source.index("if not eligible:")
        self.assertLess(eligible, not_applied)
        self.assertGreater(repair_call, eligible)


if __name__ == "__main__":
    unittest.main()
