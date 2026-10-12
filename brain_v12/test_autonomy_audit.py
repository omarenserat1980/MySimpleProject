import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.autonomy_audit import calculate_audit


class AutonomyAuditTests(unittest.TestCase):
    def test_counts_hosted_and_self_hosted_jobs_from_workflow_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "hosted.yml").write_text(
                "name: Hosted\non:\n  workflow_dispatch:\njobs:\n"
                "  check:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo ok\n",
                encoding="utf-8",
            )
            (root / "internal.yml").write_text(
                "name: Internal\non:\n  workflow_dispatch:\njobs:\n"
                "  execute:\n    runs-on: [self-hosted, linux, x64]\n    steps:\n      - run: echo ok\n",
                encoding="utf-8",
            )
            result = calculate_audit(root)
            self.assertEqual(result["workflow_count"], 2)
            self.assertEqual(result["job_count"], 2)
            self.assertEqual(result["all_workflows"]["github_hosted"], 1)
            self.assertEqual(result["all_workflows"]["self_hosted"], 1)
            self.assertEqual(result["all_workflows"]["runner_independence_percent"], 50.0)
            self.assertFalse(result["full_autonomy_certified"])

    def test_unknown_runner_is_counted_conservatively(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dynamic_runner = "${{ vars.CUSTOM_RUNNER }}"
            (root / "dynamic.yml").write_text(
                "name: Dynamic\non:\n  workflow_dispatch:\njobs:\n"
                "  check:\n    runs-on: " + dynamic_runner + "\n    steps:\n      - run: echo ok\n",
                encoding="utf-8",
            )
            result = calculate_audit(root)
            self.assertEqual(result["all_workflows"]["dynamic_unresolved"], 1)
            self.assertEqual(result["all_workflows"]["runner_independence_percent"], 0.0)
            self.assertEqual(len(result["unresolved_jobs"]), 1)

    def test_hardware_specific_workflow_is_visible_but_separated_from_software_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "brain-windows-real-boot.yml").write_text(
                "name: Real Boot\non:\n  workflow_dispatch:\njobs:\n"
                "  boot:\n    runs-on: [self-hosted, windows-real-boot]\n    steps:\n      - run: echo boot\n",
                encoding="utf-8",
            )
            (root / "software.yml").write_text(
                "name: Software\non:\n  workflow_dispatch:\njobs:\n"
                "  check:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo ok\n",
                encoding="utf-8",
            )
            result = calculate_audit(root)
            self.assertEqual(result["all_workflows"]["runner_independence_percent"], 50.0)
            self.assertEqual(result["software_scope_excluding_explicit_hardware_verification"]["runner_independence_percent"], 100.0)
            self.assertEqual(result["self_hosted_jobs"][0]["workflow"], "brain-windows-real-boot.yml")


    def test_local_reusable_workflow_calls_are_delegated_not_missing_runners(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "parent.yml").write_text(
                "name: Parent\non:\n  workflow_dispatch:\njobs:\n"
                "  child:\n    uses: ./.github/workflows/child.yml\n",
                encoding="utf-8",
            )
            (root / "child.yml").write_text(
                "name: Child\non:\n  workflow_call:\njobs:\n"
                "  hosted:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo ok\n",
                encoding="utf-8",
            )
            result = calculate_audit(root)
            self.assertEqual(result["job_count"], 1)
            self.assertEqual(result["all_workflows"]["github_hosted"], 1)
            self.assertEqual(result["all_workflows"]["missing"], 0)
            self.assertEqual(result["delegated_reusable_workflow_call_count"], 1)
            self.assertEqual(result["delegated_reusable_workflow_calls"][0]["workflow"], "parent.yml")

if __name__ == "__main__":
    unittest.main()
