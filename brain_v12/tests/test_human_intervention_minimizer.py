"""Regression tests for human_intervention_minimizer safe boundaries."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from brain_v12.tools import human_intervention_minimizer as tool


class HumanInterventionMinimizerTests(unittest.TestCase):
    def test_non_checkout_is_reported_without_network_or_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = tool.inspect_checkout(Path(tmp))
        self.assertFalse(report["is_git_repo"])
        self.assertIn("CHECKOUT_NOT_FOUND_OR_NOT_GIT", report["human_required"])

    def test_existing_destination_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "existing"
            destination.mkdir()
            sentinel = destination / "keep.txt"
            sentinel.write_text("keep", encoding="utf-8")
            result = tool.create_clean_checkout(destination)
            self.assertEqual(result["status"], "SKIPPED")
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_invalid_remote_blocks_inspection_before_fetch(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".git").mkdir()
            completed = Mock(returncode=0, stdout="https://example.invalid/not-the-repo.git\n", stderr="")
            with patch.object(tool, "_run", return_value=completed) as run:
                report = tool.inspect_checkout(repo)
            self.assertFalse(report["remote_ok"])
            self.assertIn("ORIGIN_REPOSITORY_NOT_CONFIRMED", report["human_required"])
            self.assertEqual(run.call_count, 1)


if __name__ == "__main__":
    unittest.main()
