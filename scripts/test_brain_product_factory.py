"""Regression tests for the strategy-to-product factory contract."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("brain_product_factory.py").resolve()
STRATEGIES = (
    "brain_owned_digital_product",
    "brain_owned_game",
    "micro_saas",
    "open_source_bounty",
    "sponsorship",
    "free_ai_demo",
)


class BrainProductFactoryTests(unittest.TestCase):
    def test_every_revenue_strategy_has_a_safe_build_plan(self):
        for strategy_id in STRATEGIES:
            with self.subTest(strategy_id=strategy_id), tempfile.TemporaryDirectory() as td:
                state = Path(td) / ".brain_state"
                state.mkdir()
                (state / "revenue_strategy.json").write_text(
                    json.dumps({"recommended_next": strategy_id}),
                    encoding="utf-8",
                )

                result = subprocess.run(
                    [sys.executable, str(SCRIPT)],
                    cwd=td,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

                plan = json.loads(
                    (state / "product_factory_plan.json").read_text(encoding="utf-8")
                )
                self.assertEqual(plan["strategy_id"], strategy_id)
                self.assertTrue(plan["product"]["product_id"])
                self.assertEqual(plan["stage"], "BUILD_PLAN_READY")
                self.assertEqual(plan["financial_authority"], "NONE")
                self.assertEqual(plan["external_publication"], "BLOCKED")
                self.assertEqual(plan["external_submission"], "BLOCKED")
                self.assertEqual(plan["payment"], "NOT_VERIFIED")
                self.assertEqual(plan["cost_tracking"]["money_spent"], 0)
                self.assertFalse(plan["revenue_forecast"]["counts_as_revenue"])

    def test_unknown_strategy_fails_with_explicit_diagnostic(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / ".brain_state"
            state.mkdir()
            (state / "revenue_strategy.json").write_text(
                json.dumps({"recommended_next": "unknown_strategy"}),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(SCRIPT)],
                cwd=td,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("UNSUPPORTED_RECOMMENDED_STRATEGY", result.stderr)


if __name__ == "__main__":
    unittest.main()
