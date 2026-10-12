from __future__ import annotations

import unittest

from brain_v12.virtual_hardware.computer import VirtualComputer
from brain_v12.virtual_hardware.power_thermal import PowerThermalModel
from brain_v12.virtual_hardware.api import router


class MachineManifestTests(unittest.TestCase):
    def test_versioned_manifest_contains_machine_components_units_and_provenance(self):
        machine = VirtualComputer(
            "manifest-v2", ram_size=256, cpu_profile_id="intel-core-i7-6700",
            ram_profile_id="micron-ddr5-5600-x16", cache_enabled=True,
            storage_profile_id="samsung-990-pro-1tb", gpu_profile_id="nvidia-tesla-t4",
            nic_profile_id="intel-i225-v", motherboard_profile_id="brain-pcie-gen4-x24",
        )
        manifest = machine.hardware_manifest()
        self.assertEqual(manifest["schema_version"], 2)
        self.assertTrue(manifest["validation"]["ok"], manifest["validation"])
        categories = set(manifest["validation"]["categories"])
        self.assertTrue({"cpu", "memory", "cache", "motherboard", "bus", "gpu", "network",
                         "storage", "firmware", "power", "thermal"}.issubset(categories))
        for component in manifest["components"]:
            self.assertIn("sources", component)
            self.assertIn("units", component)
            self.assertIn("fidelity", component)
            self.assertIn("unsupported_features", component)
        cpu = next(x for x in manifest["components"] if x["category"] == "cpu")
        self.assertEqual(cpu["profile_id"], "intel-core-i7-6700")
        self.assertEqual(cpu["units"]["base_clock_hz"], "Hz")
        power = next(x for x in manifest["components"] if x["category"] == "power")
        self.assertFalse(power["parameters"]["tdp_sum_is_complete_system_power"])

    def test_manifest_validation_gates_boot_and_status_exposes_telemetry(self):
        machine = VirtualComputer("boot-gate", ram_size=32)
        self.assertTrue(machine.validate_configuration()["ok"])
        status = machine.power_on()
        self.assertTrue(status["powered"])
        self.assertTrue(status["machine_manifest_validation"]["ok"])
        self.assertIn("temperature_c_estimate", status["power_thermal"])
        self.assertEqual(machine.shutdown()["powered"], False)

    def test_missing_motherboard_profile_fails_manifest_gate(self):
        machine = VirtualComputer("no-board", motherboard_profile_id=None)
        report = machine.validate_configuration()
        self.assertFalse(report["ok"])
        with self.assertRaisesRegex(RuntimeError, "BRAIN_MACHINE_MANIFEST_INVALID"):
            machine.power_on()

    def test_checkpoint_restore_recovers_virtual_state_and_detects_tampering(self):
        machine = VirtualComputer("checkpoint-vm", ram_size=64, storage_profile_id="samsung-870-evo-1tb")
        machine.power_on()
        machine.ram.write(5, 77)
        machine.storage.write("/data/safe", b"durable")
        machine.storage.flush()
        machine.storage.write("/data/volatile", b"not-durable")
        machine.nic.inject(b"packet")
        machine.gpu.pixel(0, 0, 9)
        checkpoint = machine.checkpoint()
        machine.ram.write(5, 0)
        machine.storage.write("/data/safe", b"changed")
        restored = machine.restore_checkpoint(checkpoint)
        self.assertTrue(restored["ok"])
        self.assertFalse(machine.powered)
        self.assertEqual(machine.ram.read(5), 77)
        self.assertEqual(machine.storage.read("/data/safe"), b"durable")
        self.assertEqual(machine.storage.read("/data/volatile"), b"not-durable")
        self.assertEqual(machine.nic.receive(), b"packet")
        self.assertEqual(machine.gpu.framebuffer[0], 9)
        tampered = dict(checkpoint)
        tampered["machine_id"] = "other-machine"
        with self.assertRaisesRegex(ValueError, "BRAIN_CHECKPOINT_CHECKSUM_INVALID"):
            machine.restore_checkpoint(tampered)
        machine.power_on()
        self.assertEqual(machine.ram.read(5), 77)

    def test_checkpoint_rejects_different_machine_configuration(self):
        source = VirtualComputer("same-id", ram_size=64)
        checkpoint = source.checkpoint()
        target = VirtualComputer("same-id", ram_size=128)
        with self.assertRaisesRegex(ValueError, "BRAIN_CHECKPOINT_CONFIGURATION_MISMATCH"):
            target.restore_checkpoint(checkpoint)

    def test_power_thermal_model_is_deterministic_throttles_and_recovers(self):
        def run():
            model = PowerThermalModel(thermal_capacity_j_per_c=60, cooling_w_per_c=2.5,
                                      throttle_c=35, shutdown_c=90, idle_power_watts=10,
                                      peak_power_watts=100)
            hot1 = model.update(1.0, 30.0, power_watts=100)
            hot2 = model.update(1.0, 10.0, power_watts=100)
            cool = model.update(0.0, 120.0, power_watts=0)
            return hot1, hot2, cool
        first = run()
        second = run()
        self.assertEqual(first, second)
        self.assertTrue(first[1]["throttled_estimate"])
        self.assertLess(first[2]["temperature_c_estimate"], first[1]["temperature_c_estimate"])
        self.assertFalse(first[2]["throttled_estimate"])
        self.assertFalse(first[2]["temperature_is_physical_measurement"])

    def test_thermal_fault_injection_is_explicit(self):
        model = PowerThermalModel()
        model.inject_fault("cooling_failure")
        result = model.update(1.0, 10.0)
        self.assertFalse(result["cooling_enabled"])
        model.inject_fault("sensor_failure")
        self.assertEqual(model.update(0.2, 1.0)["sensor_status"], "faulted")
        model.inject_fault("power_interruption")
        self.assertTrue(model.update(0.0, 1.0)["power_interrupted"])

    def test_existing_api_router_exposes_machine_lifecycle(self):
        routes = {(route.path, tuple(sorted(route.methods or []))) for route in router.routes}
        self.assertTrue(any(path.endswith("/profiles") and "GET" in methods for path, methods in routes))
        self.assertTrue(any(path.endswith("/machines") and "POST" in methods for path, methods in routes))
        self.assertTrue(any(path.endswith("/boot") and "POST" in methods for path, methods in routes))
        self.assertTrue(any(path.endswith("/workloads") and "POST" in methods for path, methods in routes))
        self.assertTrue(any(path.endswith("/checkpoint") and "POST" in methods for path, methods in routes))
        self.assertTrue(any(path.endswith("/restore") and "POST" in methods for path, methods in routes))
        self.assertTrue(any(path.endswith("/shutdown") and "POST" in methods for path, methods in routes))


if __name__ == "__main__":
    unittest.main()
