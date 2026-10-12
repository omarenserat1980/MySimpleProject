import unittest

from brain_v12.virtual_hardware.power_thermal import (
    FaultController, FaultType, PowerThermalModel, PowerThermalProfile, default_profile,
)


class PowerThermalTests(unittest.TestCase):
    def test_estimates_are_explicit_and_workload_dependent(self):
        model = PowerThermalModel(default_profile("cpu0", "cpu"))
        model.set_workload(0)
        idle = model.estimated_power_watts()
        model.set_workload(1)
        peak = model.estimated_power_watts()
        self.assertLess(idle, peak)
        self.assertEqual(model.profile.evidence_label(), "ESTIMATE_NOT_PHYSICALLY_CALIBRATED")

    def test_thermal_inertia_and_cooling_recovery(self):
        model = PowerThermalModel(default_profile("cpu0", "cpu"))
        model.set_workload(1)
        hot = [model.advance(10) for _ in range(120)]
        self.assertGreater(hot[-1].temperature_c, 25)
        model.set_workload(0)
        cool = [model.advance(10) for _ in range(120)]
        self.assertLess(cool[-1].temperature_c, hot[-1].temperature_c)
        replay = PowerThermalModel(default_profile("cpu0", "cpu"))
        replay.set_workload(1)
        for _ in range(120):
            replay.advance(10)
        replay.set_workload(0)
        for _ in range(120):
            replay.advance(10)
        self.assertAlmostEqual(replay.temperature_c, model.temperature_c, places=10)

    def test_throttle_and_fan_curve(self):
        profile = PowerThermalProfile("gpu0", "gpu", idle_watts=20, max_watts=300,
            thermal_resistance_c_per_w=0.5, thermal_capacitance_j_per_c=100,
            cooling_effectiveness=0.2, temperature_limit_c=80, throttle_start_c=35,
            fan_curve_start_c=30, fan_curve_full_c=40)
        model = PowerThermalModel(profile)
        model.set_workload(1)
        results = [model.advance(2) for _ in range(200)]
        self.assertTrue(any(r.throttled for r in results))
        self.assertTrue(any(r.fan_rpm == profile.fan_max_rpm for r in results))
        self.assertTrue(all(r.estimate_label == "ESTIMATE_NOT_PHYSICALLY_CALIBRATED" for r in results))

    def test_calibration_requires_measurement_evidence(self):
        p = default_profile("cpu0", "cpu")
        self.assertFalse(p.calibrated)
        calibrated = PowerThermalProfile(**{**p.__dict__, "calibration": {
            "verified": True, "measurement_source": "bench-meter-01", "measured_at": "2026-10-12"}})
        self.assertTrue(calibrated.calibrated)

    def test_fault_injection_gated_and_deterministic_recovery(self):
        ctl = FaultController()
        with self.assertRaisesRegex(RuntimeError, "FAULT_INJECTION_DISABLED"):
            ctl.inject(FaultType.NETWORK_LOSS, target="nic0", event_id="f0")
        ctl.enabled = True
        for fault in FaultType:
            ctl.inject(fault, target="device0", event_id=fault.value, queued_task_ids=["task-a", "task-b"])
        self.assertEqual(ctl.preserved_queue_ids, ["task-a", "task-b"])
        for fault in FaultType:
            ctl.recover(fault.value, recovery_evidence={"check": "passed"})
        report = ctl.report()
        self.assertTrue(report["ok"])
        self.assertEqual(report["active_fault_ids"], [])
        self.assertTrue(all(e["recovered"] for e in report["events"]))
        self.assertEqual(report["evidence_sha256"], ctl.report()["evidence_sha256"])

    def test_duplicate_fault_ids_rejected_and_unrecovered_fault_reported(self):
        ctl = FaultController(enabled=True)
        ctl.inject("storage_timeout", target="disk0", event_id="x")
        with self.assertRaisesRegex(ValueError, "FAULT_EVENT_ID_DUPLICATE"):
            ctl.inject("device_reset", target="disk0", event_id="x")
        self.assertFalse(ctl.report()["ok"])
        with self.assertRaisesRegex(KeyError, "FAULT_NOT_ACTIVE"):
            ctl.recover("missing")

    def test_dynamics_adapts_existing_machine_without_parallel_topology(self):
        from types import SimpleNamespace
        from brain_v12.virtual_hardware.power_thermal import VirtualHardwareDynamics
        machine = SimpleNamespace(name="test-machine", devices={
            "cpu0": SimpleNamespace(device_type="cpu")}, state=SimpleNamespace(value="RUNNING"))
        dynamics = VirtualHardwareDynamics(machine, fault_controller=FaultController(enabled=True))
        dynamics.configure_device("cpu0")
        dynamics.set_workload("cpu0", 0.8)
        reading = dynamics.advance(1)
        self.assertIn("cpu0", reading["readings"])
        fault = dynamics.inject_fault("device_reset", target="cpu0", event_id="reset-1",
                                      queued_task_ids=["queued-1"])
        self.assertEqual(fault["simulated_effect"], "DEVICE_RESET_MODEL_REINITIALIZED")
        self.assertEqual(dynamics.evidence_report()["preserved_queue_ids"], ["queued-1"])
        dynamics.recover_fault("reset-1", recovery_evidence={"reset_check": "passed"})
        self.assertTrue(dynamics.evidence_report()["ok"])


if __name__ == "__main__":
    unittest.main()
