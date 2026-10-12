from __future__ import annotations

import unittest

from brain_v12.virtual_hardware.hardware_profiles import (
    ClockModel, FidelityLevel, HardwareProfile, MachineManifest,
    ProvenanceKind, synthetic_baseline_profiles,
)
from brain_v12.virtual_hardware.computer import VirtualComputer


class HardwareProfileTests(unittest.TestCase):
    def test_synthetic_profiles_declare_provenance_fidelity_and_gaps(self):
        profiles = synthetic_baseline_profiles()
        self.assertEqual({p.category for p in profiles}, {"cpu", "memory", "bus", "storage", "network", "gpu"})
        for profile in profiles:
            description = profile.describe()
            self.assertEqual(description["fidelity"], FidelityLevel.FUNCTIONAL.value)
            self.assertTrue(description["sources"])
            self.assertTrue(description["modeled_behaviors"])
            self.assertTrue(description["conformance_tests"])
        cpu = next(p for p in profiles if p.category == "cpu")
        self.assertIn("x86-64", cpu.unsupported_features)
        self.assertEqual(cpu.sources[0].kind, ProvenanceKind.SYNTHETIC_BASELINE)

    def test_profile_rejects_missing_provenance(self):
        with self.assertRaisesRegex(ValueError, "PROFILE_PROVENANCE_REQUIRED"):
            HardwareProfile("bad", "cpu", "unverified", FidelityLevel.FUNCTIONAL,
                            modeled_behaviors=("registers",), conformance_tests=("test_registers",))

    def test_clock_model_is_deterministic_and_rounds_required_cycles_up(self):
        clock = ClockModel(2_000_000)
        self.assertEqual(clock.cycles_to_seconds(4000), 0.002)
        self.assertEqual(clock.seconds_to_cycles(0.0000001), 1)
        with self.assertRaisesRegex(ValueError, "CLOCK_FREQUENCY_MUST_BE_POSITIVE"):
            ClockModel(0)

    def test_machine_manifest_reports_missing_components(self):
        cpu = synthetic_baseline_profiles()[0]
        report = MachineManifest("test-machine", 1, (cpu,)).validate()
        self.assertFalse(report["ok"])
        self.assertEqual(report["missing_categories"], ["bus", "memory", "network", "storage"])
        self.assertFalse(report["host_resources_created"])

    def test_existing_virtual_computer_exposes_valid_hardware_manifest(self):
        computer = VirtualComputer("profile-test", ram_size=128)
        report = computer.hardware_manifest()
        self.assertTrue(report["validation"]["ok"], report["validation"])
        self.assertEqual(report["validation"]["schema_version"], 2)
        self.assertGreaterEqual(report["validation"]["component_count"], 10)
        self.assertIn("motherboard", report["validation"]["categories"])
        self.assertIn("firmware", report["validation"]["categories"])
        self.assertIn("power", report["validation"]["categories"])
        self.assertIn("thermal", report["validation"]["categories"])
        memory = next(p for p in report["components"] if p["category"] == "memory")
        self.assertEqual(memory["parameters"]["default_addressable_cells"], 128)
        self.assertFalse(report["validation"]["host_resources_created"])
        self.assertIn("claim", report["validation"])


if __name__ == "__main__":
    unittest.main()
