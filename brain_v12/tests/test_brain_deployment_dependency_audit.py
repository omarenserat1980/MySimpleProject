import unittest

from brain_v12.tools.brain_deployment_dependency_audit import audit, classify_endpoint


class BrainDeploymentDependencyAuditTests(unittest.TestCase):
    def test_missing_control_plane_is_blocked(self):
        result = audit({})
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("CONTROL_PLANE_ENDPOINT_NOT_READY", result["blockers"])
        self.assertFalse(result["windows_boot_verified"])

    def test_deleted_render_endpoint_is_detected_without_disclosure(self):
        secret_url = "https://brain-control-plane-main.onrender.com/path?token=do-not-print"
        result = audit({
            "BRAIN_WINDOWS_CONTROL_PLANE_URL": secret_url,
            "GITHUB_ACTIONS": "true",
            "RUNNER_NAME": "runner-internal",
            "BRAIN_INTERNAL_RUNNER_FLAG": "1",
        })
        self.assertEqual(
            result["endpoint_classifications"]["BRAIN_WINDOWS_CONTROL_PLANE_URL"],
            "LEGACY_RENDER_ENDPOINT",
        )
        self.assertNotIn(secret_url, str(result))
        self.assertFalse(result["secret_values_emitted"])
        self.assertEqual(result["status"], "BLOCKED")

    def test_https_endpoint_does_not_itself_prove_boot(self):
        result = audit({
            "BRAIN_WINDOWS_CONTROL_PLANE_URL": "https://brain.example.invalid",
            "GITHUB_ACTIONS": "true",
            "RUNNER_NAME": "runner-internal",
            "BRAIN_INTERNAL_RUNNER_FLAG": "1",
        })
        self.assertEqual(result["status"], "READY_FOR_NEXT_GATE")
        self.assertFalse(result["network_probe_performed"])
        self.assertFalse(result["windows_boot_verified"])

    def test_custom_brain_runner_is_not_assumed_to_be_github_runner(self):
        result = audit({
            "BRAIN_WINDOWS_CONTROL_PLANE_URL": "https://brain.example.invalid",
            "BRAIN_INTERNAL_RUNNER_FLAG": "1",
            "BRAIN_RUNNER_NAME": "brain-runner-local",
        })
        self.assertFalse(result["github_actions_runner_context"])
        self.assertIn("GITHUB_ACTIONS_RUNNER_CONTEXT_NOT_PROVEN", result["blockers"])

    def test_local_http_and_embedded_credentials_are_not_accepted(self):
        self.assertEqual(classify_endpoint("http://127.0.0.1:8012"), "LOCAL_ONLY_ENDPOINT")
        self.assertEqual(
            classify_endpoint("https://user:secret@brain.example.invalid"),
            "URL_EMBEDS_CREDENTIALS_BLOCKED",
        )


if __name__ == "__main__":
    unittest.main()
