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


if __name__ == "__main__":
    unittest.main()
