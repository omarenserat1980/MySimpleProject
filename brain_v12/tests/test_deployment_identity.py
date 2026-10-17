import unittest

from brain_v12.brain.deployment_identity import deployment_identity


class DeploymentIdentityTests(unittest.TestCase):
    def test_render_metadata_is_authoritative_when_github_sha_is_absent(self):
        identity = deployment_identity({
            "RENDER_GIT_COMMIT": "new-render-sha",
            "RENDER_GIT_BRANCH": "brain-independent-executor-pool",
            "RENDER_GIT_REPO_SLUG": "omarenserat1980/MySimpleProject",
            "RENDER_SERVICE_ID": "srv-example",
            "RENDER_INSTANCE_ID": "instance-example",
            "GIT_COMMIT": "stale-sha",
        })
        self.assertEqual(identity["commit"], "new-render-sha")
        self.assertEqual(identity["expected_commit"], "new-render-sha")
        self.assertTrue(identity["converged"])
        self.assertEqual(identity["service_id"], "srv-example")
        self.assertEqual(identity["instance"], "instance-example")

    def test_stale_legacy_commit_does_not_claim_convergence(self):
        identity = deployment_identity({"GIT_COMMIT": "stale-sha"})
        self.assertEqual(identity["commit"], "stale-sha")
        self.assertFalse(identity["converged"])
        self.assertEqual(identity["expected_commit"], "")

    def test_github_actions_metadata_remains_supported(self):
        identity = deployment_identity({
            "GITHUB_SHA": "github-sha",
            "GITHUB_REF_NAME": "feature/test",
            "GITHUB_REPOSITORY": "owner/repo",
            "GITHUB_RUN_ID": "123",
            "HOSTNAME": "runner-host",
        })
        self.assertEqual(identity["commit"], "github-sha")
        self.assertTrue(identity["converged"])
        self.assertEqual(identity["branch"], "feature/test")
        self.assertEqual(identity["repository"], "owner/repo")
        self.assertEqual(identity["run_id"], "123")
        self.assertEqual(identity["instance"], "runner-host")

    def test_missing_provider_commit_does_not_claim_convergence(self):
        identity = deployment_identity({})
        self.assertEqual(identity["commit"], "unknown")
        self.assertFalse(identity["converged"])


if __name__ == "__main__":
    unittest.main()
