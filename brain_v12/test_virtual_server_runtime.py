import unittest

from brain_v12.virtual_hardware.virtual_server_runtime import BrainVirtualServerRuntime


class BrainVirtualServerRuntimeTests(unittest.TestCase):
    def test_register_start_request_stop_lifecycle(self):
        server = BrainVirtualServerRuntime()
        server.register_service("control-api", "api")
        stopped = server.request("control-api")
        self.assertFalse(stopped["ok"])
        server.start_service("control-api")
        response = server.request("control-api", "status")
        self.assertTrue(response["ok"])
        self.assertEqual(response["status"], "SIMULATED_RESPONSE")
        self.assertFalse(response["network_socket_opened"])
        server.stop_service("control-api")
        self.assertEqual(server.health()["status"], "IDLE")
        self.assertFalse(server.health()["guest_os_boot_verified"])

    def test_failure_marks_server_degraded(self):
        server = BrainVirtualServerRuntime()
        server.register_service("worker", "worker")
        server.start_service("worker")
        server.fail_service("worker", "test fault")
        health = server.health()
        self.assertFalse(health["ok"])
        self.assertEqual(health["status"], "DEGRADED")
        self.assertEqual(health["failed_services"], 1)

    def test_duplicate_and_unknown_services_are_rejected(self):
        server = BrainVirtualServerRuntime()
        server.register_service("api")
        with self.assertRaisesRegex(ValueError, "ALREADY_REGISTERED"):
            server.register_service("api")
        with self.assertRaisesRegex(KeyError, "NOT_FOUND"):
            server.start_service("missing")

    def test_external_network_is_never_enabled(self):
        server = BrainVirtualServerRuntime()
        server.register_service("web", "web")
        server.start_service("web")
        response = server.request("web")
        self.assertFalse(response["network_socket_opened"])
        self.assertFalse(server.health()["network_listener_enabled"])


    def test_checkpoint_restore_preserves_service_state_and_events(self):
        server = BrainVirtualServerRuntime(server_id="test-server")
        server.register_service("api", "api")
        server.start_service("api")
        server.request("api", "status")
        checkpoint = server.checkpoint()

        restored = BrainVirtualServerRuntime()
        health = restored.restore_checkpoint(checkpoint)
        self.assertEqual(health["server_id"], "test-server")
        self.assertEqual(health["running_services"], 1)
        self.assertEqual(restored.services["api"].requests, 1)
        self.assertEqual(restored.tick, 1)
        self.assertEqual(restored.events, server.events)
        self.assertFalse(health["network_listener_enabled"])

    def test_invalid_checkpoint_does_not_mutate_runtime(self):
        server = BrainVirtualServerRuntime(server_id="stable")
        server.register_service("api", "api")
        before = server.checkpoint()
        invalid = dict(before)
        invalid["tick"] = -1
        with self.assertRaisesRegex(ValueError, "TICK_INVALID"):
            server.restore_checkpoint(invalid)
        self.assertEqual(server.checkpoint(), before)

    def test_checkpoint_rejects_duplicate_service_names(self):
        server = BrainVirtualServerRuntime()
        checkpoint = server.checkpoint()
        checkpoint["services"] = [
            {"name": "api", "kind": "api", "state": "RUNNING", "requests": 0, "failures": 0},
            {"name": "api", "kind": "api", "state": "STOPPED", "requests": 0, "failures": 0},
        ]
        with self.assertRaisesRegex(ValueError, "SERVICE_INVALID"):
            server.restore_checkpoint(checkpoint)


if __name__ == "__main__":
    unittest.main()
