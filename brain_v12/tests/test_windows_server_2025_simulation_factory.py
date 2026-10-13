import unittest

from brain_v12.brain.windows_server_2025_simulation_factory import (
    EvidenceRecorder,
    VirtualHardwareModel,
    WindowsServer2025Simulator,
    simulate_windows_server_2025,
)


class WindowsServer2025SimulationFactoryTests(unittest.TestCase):
    def test_success_is_synthetic_and_evidence_verifies(self):
        result = simulate_windows_server_2025()
        self.assertEqual(result["status"], "SIMULATED_BOOT_SUCCESS")
        self.assertEqual(result["execution_mode"], "SIMULATION_ONLY")
        self.assertFalse(result["real_windows_boot_verified"])
        self.assertFalse(result["side_effects_performed"])
        self.assertFalse(result["external_resources_created"])
        self.assertEqual(result["host_observed_resources"]["status"], "NOT_COLLECTED")
        self.assertTrue(result["verification"]["ok"])
        self.assertTrue(all(e["evidence_type"] == "SYNTHETIC_SIMULATION_EVENT"
                            for e in result["events"]))

    def test_real_or_unknown_capability_is_blocked(self):
        for capability in ("windows-server-2025-real-boot",
                           "windows-server-2025-cloud-native", "arkan", "unknown"):
            with self.subTest(capability=capability):
                result = WindowsServer2025Simulator().run(capability=capability)
                self.assertEqual(result["status"], "BLOCKED")
                self.assertFalse(result["real_windows_boot_verified"])

    def test_failure_scenarios_fail_closed(self):
        scenarios = (
            "no_boot_disk", "invalid_boot_config", "low_disk_space",
            "service_failure", "missing_dependency", "dns_failure",
            "network_down", "out_of_memory", "cancel_during_boot",
            "stage_crash", "timeout", "driver_failure", "verification_failure",
        )
        for scenario in scenarios:
            with self.subTest(scenario=scenario):
                result = simulate_windows_server_2025(scenario)
                self.assertIn(result["status"],
                              {"SIMULATED_BOOT_FAILED", "CANCELLED"})
                self.assertIsNotNone(result["reason_code"])
                self.assertNotEqual(result["status"], "SIMULATED_BOOT_SUCCESS")

    def test_preflight_safety_scenarios_are_blocked(self):
        for scenario in ("duplicate_request", "invalid_executor_pointer",
                         "real_executor_route"):
            with self.subTest(scenario=scenario):
                result = simulate_windows_server_2025(scenario)
                self.assertEqual(result["status"], "BLOCKED")

    def test_power_loss_recovery_is_explicitly_simulated(self):
        result = simulate_windows_server_2025("power_loss_recovery")
        self.assertEqual(result["status"], "SIMULATED_BOOT_SUCCESS")
        self.assertEqual(result["recovery_status"], "SIMULATED_RECOVERY_PASS")
        self.assertFalse(result["real_windows_boot_verified"])

    def test_tampered_evidence_fails_verification(self):
        result = simulate_windows_server_2025("corrupt_evidence")
        self.assertEqual(result["status"], "SIMULATED_BOOT_FAILED")
        self.assertFalse(result["verification"]["ok"])
        self.assertEqual(result["reason_code"], "EVIDENCE_CHAIN_INVALID")

    def test_invalid_virtual_hardware_fails_preflight(self):
        result = simulate_windows_server_2025(
            hardware=VirtualHardwareModel(vcpu_count=0)
        )
        self.assertEqual(result["status"], "SIMULATED_BOOT_FAILED")
        self.assertEqual(result["reason_code"], "VCPU_COUNT_OUT_OF_RANGE")

    def test_unknown_scenario_is_blocked(self):
        self.assertEqual(simulate_windows_server_2025("not-a-scenario")["status"],
                         "BLOCKED")

    def test_wrong_virtual_hardware_types_fail_closed(self):
        result = simulate_windows_server_2025(
            hardware=VirtualHardwareModel(vcpu_count="two")
        )
        self.assertEqual(result["status"], "SIMULATED_BOOT_FAILED")
        self.assertEqual(result["reason_code"], "VCPU_COUNT_MUST_BE_INTEGER")

    def test_evidence_verifier_detects_mutation_and_reordering(self):
        recorder = EvidenceRecorder()
        recorder.record("PREFLIGHT", "PASS")
        recorder.record("FIRMWARE_CHECK", "PASS")
        events = [dict(event) for event in recorder.events]
        self.assertTrue(EvidenceRecorder.verify(events)["ok"])
        events[0]["status"] = "FAILED"
        self.assertFalse(EvidenceRecorder.verify(events)["ok"])
        reversed_events = list(reversed(recorder.events))
        self.assertFalse(EvidenceRecorder.verify(reversed_events)["ok"])

    def test_report_never_claims_real_boot(self):
        for scenario in ("success", "service_failure", "power_loss_recovery",
                         "corrupt_evidence", "real_executor_route"):
            with self.subTest(scenario=scenario):
                result = simulate_windows_server_2025(scenario)
                self.assertIs(result["real_windows_boot_verified"], False)
                self.assertEqual(result["execution_mode"], "SIMULATION_ONLY")


if __name__ == "__main__":
    unittest.main()
