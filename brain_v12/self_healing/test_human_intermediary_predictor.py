import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain_v12.self_healing import human_intermediary_predictor as p


class HumanIntermediaryPredictorTests(unittest.TestCase):
    def test_frontier_is_earliest_incomplete_task(self):
        parsed = {
            0: [(True, "done")],
            1: [(True, "done"), (False, "diagnostics")],
            2: [(False, "watch recent workflow runs automatically")],
        }
        self.assertEqual(p.choose_frontier(parsed), (1, "diagnostics", 1))

    def test_no_regression(self):
        with tempfile.TemporaryDirectory() as td:
            old = p.STATE_FILE
            p.STATE_FILE = Path(td) / "state.json"
            p.STATE_DIR = Path(td)
            state = {"schema": "brain-human-intermediary-state/v1", "max_phase": 2, "max_step": 4}
            p.STATE_FILE.write_text(json.dumps(state), encoding="utf-8")
            out = p.persist_monotonic(state, 1, 0, {"prediction": ["x"]})
            self.assertEqual(out["max_phase"], 2)
            self.assertEqual(out["max_step"], 4)
            self.assertTrue(out["regression_blocked"])
            p.STATE_FILE = old

    def test_safe_action_never_edits_code(self):
        action = p.safe_action_for("apply only approved repair scopes", {})
        self.assertEqual(action["mode"], "fail_closed")
        self.assertFalse(action["executed"])

    @patch.object(p, "api_get", return_value={"available": False, "reason": "no_github_token"})
    def test_report_without_token_is_still_bounded(self, _api):
        with tempfile.TemporaryDirectory() as td:
            old_dir, old_state, old_report = p.STATE_DIR, p.STATE_FILE, p.REPORT_FILE
            p.STATE_DIR = Path(td)
            p.STATE_FILE = Path(td) / "state.json"
            p.REPORT_FILE = Path(td) / "prediction.json"
            with patch.object(p, "roadmap", return_value="## Phase 0\n- [x] done\n## Phase 1\n- [ ] next"):
                with patch.object(p, "history_messages", return_value=["fix: verify evidence", "continue next step"]):
                    report = p.build_report()
            self.assertEqual(report["current_frontier"]["phase"], 1)
            self.assertEqual(report["next_safe_action"]["mode"], "fail_closed")
            p.STATE_DIR, p.STATE_FILE, p.REPORT_FILE = old_dir, old_state, old_report


if __name__ == "__main__":
    unittest.main()
