import unittest
from brain_v12.virtual_hardware.cpu import VirtualCPU, cpu_profile_metadata
from brain_v12.virtual_hardware.memory import VirtualRAM

class CPUEmulationTests(unittest.TestCase):
    def test_legacy_program_and_reproducibility(self):
        program=[("MOVI",0,7),("MOVI",1,5),("ADD",0,1),("OUT",0),("HALT",)]
        runs=[]
        for _ in range(2):
            c=VirtualCPU(); r=c.run(program,VirtualRAM())
            runs.append((r["registers"],r["output"],r["cycles"]))
        self.assertEqual(runs[0],runs[1]); self.assertEqual(runs[0][1],[12])
    def test_profiles_are_metadata_not_native_isa(self):
        for name in ("brainvm-baseline","intel-core-i7-12700k-reference","amd-epyc-9654-reference"):
            m=cpu_profile_metadata(name); self.assertFalse(m["native_isa_supported"]); self.assertFalse(m["cycle_accurate"])
    def test_cache_estimates_and_memory(self):
        c=VirtualCPU(); r=c.run([("MOVI",0,42),("STORE",0,8),("LOAD",1,8),("LOAD",2,8),("HALT",)],VirtualRAM(128))
        self.assertEqual(r["registers"][1:3],[42,42]); self.assertGreater(r["estimated_cycles_this_run"],r["cycles"])
        self.assertGreater(r["cache_stats"]["l1_hits"],0)
    def test_invalid_profile_and_opcode(self):
        with self.assertRaisesRegex(ValueError,"CPU_PROFILE_UNSUPPORTED"): VirtualCPU(profile_name="unknown")
        with self.assertRaisesRegex(RuntimeError,"CPU_ILLEGAL_OPCODE:VADDPS"): VirtualCPU().step([("VADDPS",)],VirtualRAM())
    def test_bounds_cycle_limit_and_flags(self):
        with self.assertRaises(IndexError): VirtualCPU().step([("LOAD",0,20)],VirtualRAM(8))
        with self.assertRaisesRegex(RuntimeError,"CPU_CYCLE_LIMIT"): VirtualCPU().run([("JMP",0)],VirtualRAM(),3)
        r=VirtualCPU().run([("MOVI",0,4),("MOVI",1,4),("SUB",0,1),("JZ",4),("HALT",)],VirtualRAM())
        self.assertTrue(r["flags"]["zero"])
if __name__=="__main__": unittest.main()
