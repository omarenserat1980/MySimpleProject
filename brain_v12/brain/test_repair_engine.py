import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.repair_engine import RepairEngine


class RepairEngineTests(unittest.TestCase):
    def test_known_verification_failure_gets_exact_safe_plan(self):
        log = "verification_suite.py: ValueError: not enough values to unpack (expected 4, got 0)"
        plan = RepairEngine().plan(log)
        self.assertEqual(plan.classification, "VERIFICATION_VM_NOT_LOADED")
        self.assertEqual(plan.action, "APPLY_EXACT_PATCH")
        self.assertTrue(plan.safe)

    def test_unknown_source_failure_is_not_mutated(self):
        engine = RepairEngine()
        with tempfile.TemporaryDirectory() as d:
            plan, ok = engine.repair(d, "Traceback: AssertionError in random_module.py")
            self.assertFalse(ok)
            self.assertEqual(plan.action, "BLOCK_FOR_REVIEW")

    def test_exact_patch_rolls_back_when_validation_fails(self):
        engine = RepairEngine()
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "brain_v12/verification"
            p.mkdir(parents=True)
            f = p / "verification_suite.py"
            original = "vm = BrainVM()\nr = vm.run(max_steps=1000)"
            f.write_text(original, encoding="utf-8")
            log = "verification_suite.py: ValueError: not enough values to unpack"
            plan = engine.plan(log)
            self.assertTrue(engine.apply(d, plan))
            self.assertNotEqual(f.read_text(encoding="utf-8"), original)
            # Validation command cannot succeed in this fixture; repair() must restore it.
            plan2, ok = engine.repair(d, log)
            self.assertFalse(ok)
            self.assertEqual(f.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
