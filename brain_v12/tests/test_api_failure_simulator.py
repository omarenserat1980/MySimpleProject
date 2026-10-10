import unittest

from brain_v12.brain.api_failure_simulator import diagnose_api_state


class ApiFailureSimulatorTests(unittest.TestCase):
    def test_refused_and_stopped_process_points_to_startup_diagnostics(self):
        result = diagnose_api_state(port_state="REFUSED", process_running=False)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "API_UNREACHABLE")
        self.assertEqual(result["reality"], "SIMULATED")
        self.assertIn("startup logs", result["next_step"])

    def test_refused_but_process_running_checks_listener(self):
        result = diagnose_api_state(port_state="REFUSED", process_running=True)
        self.assertIn("bind address", result["next_step"])
        self.assertEqual(result["reality"], "SIMULATED")

    def test_timeout_is_not_mislabeled_as_refused(self):
        result = diagnose_api_state(port_state="TIMEOUT", process_running=True)
        self.assertEqual(result["status"], "API_TIMEOUT")
        self.assertIn("firewall", result["next_step"])

    def test_success_http_requires_separate_readiness_and_auth_checks(self):
        result = diagnose_api_state(port_state="HTTP", http_status=200)
        self.assertEqual(result["status"], "API_REACHABLE")
        self.assertIn("authentication", result["next_step"])

    def test_auth_rejection_does_not_recommend_printing_secrets(self):
        result = diagnose_api_state(port_state="HTTP", http_status=401)
        self.assertEqual(result["status"], "AUTH_REJECTED")
        self.assertIn("without printing or logging secrets", result["next_step"])
        self.assertEqual(result["reality"], "SIMULATED")

    def test_unknown_http_status_fails_closed(self):
        result = diagnose_api_state(port_state="HTTP", http_status=503)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "UNCLASSIFIED_HTTP_STATUS")
        self.assertEqual(result["reality"], "SIMULATED")

    def test_unknown_state_fails_closed(self):
        result = diagnose_api_state(port_state="MAGIC", process_running=True)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "UNSUPPORTED_SIMULATED_STATE")
        self.assertEqual(result["reality"], "SIMULATED")


if __name__ == "__main__":
    unittest.main()
