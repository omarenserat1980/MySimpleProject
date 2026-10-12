import unittest

from brain_v12.virtual_hardware.cpu import VirtualCPU, cpu_profile_metadata
from brain_v12.virtual_hardware.memory import VirtualRAM


class CPUEmulationTests(unittest.TestCase):
    def test_legacy_program_is_reproducible(self):
        program = [("MOVI", 0, 7), ("MOVI", 1, 5), ("ADD", 0, 1), ("OUT", 0), ("HALT",)]
        results = []
        for _ in range(2):
            cpu = VirtualCPU()
            result = cpu.run(program, VirtualRAM())
            results.append((result["registers"], result["output"], result["cycles"]))
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0][1], [12])

    def test_reference_profiles_do_not_claim_native_isa(self):
        for name in ("brainvm-baseline", "intel-core-i7-12700k-reference", "amd-epyc-9654-reference"):
            metadata = cpu_profile_metadata(name)
            self.assertFalse(metadata["native_isa_supported"])
            self.assertFalse(metadata["cycle_accurate"])
            self.assertFalse(metadata["pipeline_modeled"])

    def test_memory_estimates_are_separate_from_functional_cycles(self):
        cpu = VirtualCPU()
        result = cpu.run([("MOVI", 0, 42), ("STORE", 0, 8), ("LOAD", 1, 8),
                          ("LOAD", 2, 8), ("HALT",)], VirtualRAM(128))
        self.assertEqual(result["registers"][1:3], [42, 42])
        self.assertGreater(result["estimated_cycles_this_run"], result["cycles"])
        self.assertGreater(result["cache_stats"]["l1_hits"], 0)

    def test_unknown_profile_and_opcode_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "CPU_PROFILE_UNSUPPORTED"):
            VirtualCPU(profile_name="unknown")
        with self.assertRaisesRegex(RuntimeError, "CPU_ILLEGAL_OPCODE:VADDPS"):
            VirtualCPU().step([("VADDPS",)], VirtualRAM())

    def test_bounds_and_cycle_limit(self):
        with self.assertRaises(IndexError):
            VirtualCPU().step([("LOAD", 0, 20)], VirtualRAM(8))
        with self.assertRaisesRegex(RuntimeError, "CPU_CYCLE_LIMIT"):
            VirtualCPU().run([("JMP", 0)], VirtualRAM(), 3)


if __name__ == "__main__":
    unittest.main()
