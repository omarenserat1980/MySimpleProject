import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain_v12.self_healing import future_evolution


class FutureEvolutionTests(unittest.TestCase):
    def test_plan_schema_and_execution_policy(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td)
            with patch.object(future_evolution, "STATE", state),                  patch.object(future_evolution, "PLAN", state / "future_evolution_plan.json"),                  patch.object(future_evolution, "run", side_effect=[(0, "PREDICTIVE"), (0, "IMPROVEMENT")]),                  patch.object(future_evolution, "runtime_predictions", return_value=[{
                     "type": "runtime_dependency",
                     "id": "dependency:example",
                     "prediction": "dependency_missing",
                     "risk": "high",
                     "evidence": "not_importable_in_current_runtime",
                 }]),                  patch.object(future_evolution, "recent_failures", return_value=[]):
                plan = future_evolution.predict()

            self.assertEqual(plan["schema"], "brain-future-evolution/v1")
            self.assertEqual(plan["objective"], "predict -> prevent -> evolve -> verify -> learn -> repeat")
            self.assertTrue(plan["execution_policy"]["auto_execute"])
            self.assertFalse(plan["execution_policy"]["unverified_changes_allowed"])
            saved = json.loads((state / "future_evolution_plan.json").read_text())
            self.assertEqual(saved["predicted_development_count"], 1)

    def test_recent_failures_become_predictions(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td)
            history = state / "continuous_evolution_history.jsonl"
            history.write_text(json.dumps({
                "cycle": 7,
                "status": "FAILED",
                "review_exit_code": 1,
                "repair_exit_code": 1,
            }) + "\n")
            with patch.object(future_evolution, "STATE", state):
                rows = future_evolution.recent_failures()
            self.assertEqual(rows[0]["type"], "recurring_failure")
            self.assertEqual(rows[0]["prediction"], "repeat_failure_until_root_cause_removed")


if __name__ == "__main__":
    unittest.main()
