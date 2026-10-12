import unittest

from brain_v12.brain.execution_coordinator import BrainExecutionCoordinator
from brain_v12.brain.github_execution_bridge import BrainGitHubExecutionBridge
from brain_v12.github_agent import BrainGitHubAgent


class GitHubExecutionBridgeTests(unittest.TestCase):
    def _bridge(self, calls=None):
        calls = calls if calls is not None else []
        tool_map = {
            "get_repo": lambda **kwargs: calls.append(kwargs) or {"ok": True, "repo": "brain"},
        }
        return BrainGitHubExecutionBridge(
            BrainGitHubAgent(tool_map),
            BrainExecutionCoordinator(),
        )

    def test_read_only_github_execution_completes_only_with_evidence(self):
        bridge = self._bridge()
        created = bridge.create("repository", max_attempts=2)
        result = bridge.execute(
            created["control"]["id"],
            "repository",
            verifier=lambda value: {
                "verified": value["result"]["ok"] is True,
                "evidence_ref": "evidence://github/repository/1",
            },
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "VERIFIED_COMPLETED")
        self.assertEqual(result["task"]["status"], "COMPLETED")

    def test_mutation_requires_approval_before_executor_runs(self):
        calls = []
        bridge = self._bridge(calls)
        created = bridge.create("code_write", max_attempts=2)
        result = bridge.execute(
            created["control"]["id"],
            "code_write",
            verifier=lambda _: {"verified": True, "evidence_ref": "evidence://bad"},
        )
        self.assertFalse(result["ok"])
        self.assertTrue(result["error"].startswith("EXECUTOR_ERROR:PermissionError"))
        self.assertEqual(calls, [])

    def test_verification_failure_retries_and_records_repair(self):
        bridge = self._bridge()
        created = bridge.create("repository", max_attempts=2)
        result = bridge.execute(
            created["control"]["id"],
            "repository",
            verifier=lambda _: {"verified": False},
            repair=lambda failure: {"ok": True, "action": "diagnose-and-retry"},
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "RETRYING")
        self.assertEqual(result["repair"]["action"], "diagnose-and-retry")
        self.assertTrue(any(e["stage"] == "repair" for e in result["control"]["evidence"]))

    def test_transport_success_without_domain_evidence_never_completes(self):
        bridge = self._bridge()
        created = bridge.create("repository", max_attempts=1)
        result = bridge.execute(
            created["control"]["id"],
            "repository",
            verifier=lambda _: {"verified": True},
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "VERIFICATION_EVIDENCE_REQUIRED")
        self.assertEqual(result["task"]["status"], "FAILED")


if __name__ == "__main__":
    unittest.main()
