from __future__ import annotations

import unittest

from brain_v12.virtual_hardware.cpu_profiles import get_cpu_profile, list_cpu_profiles
from brain_v12.virtual_hardware.x86_64 import X86_64CPU, X86UnsupportedInstruction
from brain_v12.virtual_hardware.computer import VirtualComputer
from brain_v12.blade_server import BladeChassis, BladeScheduler


class CPUProfileTests(unittest.TestCase):
    def test_real_reference_profiles_carry_sources_and_explicit_gaps(self):
        profiles = {p["profile_id"]: p for p in list_cpu_profiles()}
        self.assertIn("intel-core-i7-6700", profiles)
        self.assertIn("amd-ryzen-5-5600", profiles)
        for key in ("intel-core-i7-6700", "amd-ryzen-5-5600"):
            p = profiles[key]
            self.assertTrue(p["specification_urls"])
            self.assertEqual(p["fidelity"], "functional_subset")
            self.assertFalse(p["physical_performance_claim"])
            self.assertEqual(p["microarchitecture_simulation"], "not_implemented")
            self.assertIn("complete x86-64 instruction set", p["unsupported_features"])

    def test_unknown_profile_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "UNKNOWN_CPU_PROFILE"):
            get_cpu_profile("made-up-cpu")

    def test_profile_selection_does_not_claim_microarchitecture(self):
        cpu = X86_64CPU(profile_id="intel-core-i7-6700")
        self.assertEqual(cpu.profile["model"], "Intel Core i7-6700 (Skylake desktop reference)")
        self.assertEqual(cpu.profile["fidelity"], "functional_subset")
        self.assertFalse(cpu.profile["physical_performance_claim"])

    def test_reference_instruction_vector_wrap_flags_and_output(self):
        cpu = X86_64CPU()
        result = cpu.run([
            ("MOVI", "RAX", (1 << 64) - 1),
            ("MOVI", "RBX", 1),
            ("ADD", "RAX", "RBX"),
            ("OUT", "RAX"),
            ("HLT",),
        ])
        self.assertEqual(result["registers"]["RAX"], 0)
        self.assertEqual(result["output"], [0])
        self.assertTrue(result["flags"]["CF"])
        self.assertTrue(result["flags"]["ZF"])
        self.assertEqual(result["cycles"], 5)
        self.assertEqual(result["counter_semantics"], "interpreted_symbolic_instruction")

    def test_signed_overflow_and_subtraction_flags(self):
        cpu = X86_64CPU()
        cpu.run([
            ("MOVI", "RAX", (1 << 63) - 1),
            ("MOVI", "RBX", 1),
            ("ADD", "RAX", "RBX"),
            ("HLT",),
        ])
        self.assertTrue(cpu.flags["OF"])
        self.assertTrue(cpu.flags["SF"])
        cpu.reset()
        cpu.run([("MOVI", "RAX", 0), ("MOVI", "RBX", 1), ("CMP", "RAX", "RBX"), ("HLT",)])
        self.assertTrue(cpu.flags["CF"])
        self.assertFalse(cpu.flags["ZF"])
        self.assertEqual(cpu.registers["RAX"], 0)

    def test_unknown_instruction_reports_opcode_profile_and_rip(self):
        cpu = X86_64CPU(profile_id="amd-ryzen-5-5600")
        with self.assertRaises(X86UnsupportedInstruction) as caught:
            cpu.step([("VADDPS",)])
        exc = caught.exception
        self.assertEqual(exc.opcode, "VADDPS")
        self.assertEqual(exc.rip, 0)
        self.assertEqual(exc.profile_id, "amd-ryzen-5-5600")
        self.assertIn("X86_UNSUPPORTED_OPCODE:VADDPS", str(exc))
        self.assertFalse(cpu.unsupported_instruction_report("VADDPS")["binary_instruction_decoding"])

    def test_register_and_privilege_validation(self):
        with self.assertRaisesRegex(ValueError, "X86_PRIVILEGE_LEVEL_INVALID"):
            X86_64CPU(privilege_level=4)
        cpu = X86_64CPU()
        with self.assertRaisesRegex(RuntimeError, "X86_BAD_REGISTER"):
            cpu.step([("MOVI", "CR0", 1)])

    def test_virtual_computer_selects_cpu_profile_and_reports_manifest(self):
        computer = VirtualComputer("profiled", ram_size=64, cpu_profile_id="intel-core-i7-6700")
        computer.power_on()
        result = computer.execute([("MOVI", "RAX", 9), ("HLT",)])
        self.assertEqual(result["registers"]["RAX"], 9)
        manifest = computer.hardware_manifest()
        cpu_profile = next(item for item in manifest["components"] if item["category"] == "cpu")
        self.assertEqual(cpu_profile["profile_id"], "intel-core-i7-6700")
        self.assertEqual(cpu_profile["fidelity"], "functional")
        self.assertIn("binary x86 instruction-byte decoding", cpu_profile["unsupported_features"])
        self.assertEqual(computer.status()["cpu"]["profile_id"], "intel-core-i7-6700")

    def test_profiled_cpu_runs_through_existing_blade_scheduler(self):
        chassis = BladeChassis("cpu-profile-test")
        blade = chassis.create_blade(cpu_profile_id="amd-ryzen-5-5600")
        blade.power_on()
        scheduler = BladeScheduler(chassis)
        result = scheduler.dispatch([("MOVI", "RAX", 17), ("HLT",)])
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["result"]["result"]["registers"]["RAX"], 17)
        self.assertEqual(result["result"]["result"]["profile"]["profile_id"], "amd-ryzen-5-5600")

    def test_interrupts_are_reported_as_queued_not_falsely_delivered(self):
        cpu = X86_64CPU()
        result = cpu.request_interrupt(32)
        self.assertTrue(result["queued"])
        self.assertFalse(result["delivered"])
        self.assertEqual(cpu.pending_interrupts, [32])
        with self.assertRaisesRegex(ValueError, "X86_INTERRUPT_VECTOR_OUT_OF_RANGE"):
            cpu.request_interrupt(256)


if __name__ == "__main__":
    unittest.main()
