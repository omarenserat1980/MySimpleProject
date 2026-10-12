import unittest

from tools.diagnose_cloud_worker_wiring import diagnose


class WorkerWiringTests(unittest.TestCase):
    def test_api_only_render_command_is_blocked(self):
        result = diagnose({
            "name": "brain-control-plane-main",
            "type": "web_service",
            "serviceDetails": {
                "runtime": "python",
                "envSpecificDetails": {
                    "startCommand": "uvicorn brain_v12.app:app --host 0.0.0.0 --port $PORT"
                },
            },
        })
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("API_ONLY_START_COMMAND", result["findings"])
        self.assertFalse(result["worker_launch_proven"])

    def test_worker_launch_is_not_mistaken_for_health_proof(self):
        result = diagnose({
            "name": "brain-worker",
            "type": "background_worker",
            "serviceDetails": {
                "runtime": "python",
                "envSpecificDetails": {
                    "startCommand": "python -m brain_v12.cloud_runtime.worker"
                },
            },
        })
        self.assertEqual(result["status"], "REQUIRES_WORKER_HEALTH_PROOF")
        self.assertTrue(result["worker_launch_proven"])

    def test_unknown_start_command_fails_closed(self):
        result = diagnose({"name": "unknown", "type": "web_service", "serviceDetails": {}})
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("WORKER_START_COMMAND_NOT_PROVEN", result["findings"])


if __name__ == "__main__":
    unittest.main()
