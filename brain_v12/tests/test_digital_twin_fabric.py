import tempfile,unittest
from brain_v12.brain.digital_twin_fabric import DigitalTwinFabric,Reality,RealityGate

class DigitalTwinTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.f=DigitalTwinFabric(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def test_simulation_cannot_prove_real(self):
        e={"reality":"SIMULATED","source":"digital-twin","boot_verified":True}
        self.assertFalse(self.f.reality_gate(e,"REAL")["ok"])
    def test_real_evidence_requires_real_source(self):
        self.assertTrue(self.f.reality_gate({"reality":"REAL","source":"windows-installed-disk"},"REAL")["ok"])
    def test_twin_snapshot_is_hashed_and_simulated(self):
        t=self.f.create("emu-win")
        t.emulator.write_file("a.txt","x")
        s=t.snapshot("baseline")["snapshot"]
        self.assertEqual(s["reality"],"SIMULATED")
        self.assertEqual(len(s["sha256"]),64)
        self.assertTrue(t.restore_metadata(s["snapshot_id"])["ok"])
    def test_fault_injection_is_bounded(self):
        t=self.f.create("emu-fault")
        self.assertTrue(t.inject_failure("network_down")["ok"])
        self.assertFalse(t.inject_failure("unknown")["ok"])
    def test_twin_limit(self):
        f=DigitalTwinFabric(self.tmp.name,policy=type("P",(),{"max_twins":1})())
        f.create("a")
        with self.assertRaises(RuntimeError): f.create("b")
    def test_compare(self):
        self.assertTrue(self.f.compare({"os":"x"},{"os":"x"})["ok"])
        self.assertFalse(self.f.compare({"os":"x"},{"os":"y"})["ok"])
if __name__=="__main__": unittest.main()
