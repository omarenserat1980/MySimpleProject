import tempfile,unittest
from brain_v12.brain.arkan_device_emulator import ArkanDeviceEmulator,ArkanProfile

class ArkanEmulatorTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.a=ArkanDeviceEmulator(self.tmp.name)
 def tearDown(self): self.tmp.cleanup()
 def test_identity_matches_arkan_profile(self):
  i=self.a.info(); self.assertEqual(i["device"]["name"],"arkan"); self.assertEqual(i["device"]["logical_cpus"],8); self.assertEqual(i["device"]["architecture"],"x64")
 def test_readiness_has_hard_gates(self):
  r=self.a.readiness(); self.assertFalse(r["ok"]); self.assertFalse(r["checks"]["kvm"])
  self.a.set_network(kvm=True); self.assertTrue(self.a.readiness()["ok"])
 def test_resource_pressure_blocks(self):
  self.a.set_network(kvm=True); self.a.set_resources(free_ram_gib=1.0)
  self.assertFalse(self.a.readiness()["ok"]); self.assertFalse(self.a.readiness()["checks"]["memory_gate"])
 def test_fault_and_recovery(self):
  self.a.inject_fault("network_down"); self.assertFalse(self.a.heartbeat()["state"]=="ONLINE")
  self.a.clear_faults(); self.assertEqual(self.a.heartbeat()["state"],"ONLINE")
 def test_service_and_vm_faults(self):
  self.a.inject_fault("runner_offline"); self.assertFalse(self.a.readiness()["checks"]["runner"])
  self.a.clear_faults(); self.a.set_network(kvm=True); self.assertTrue(self.a.readiness()["checks"]["runner"])
 def test_snapshot_is_simulated_and_hashed(self):
  s=self.a.snapshot("baseline"); self.assertEqual(s["reality"],"SIMULATED"); self.assertEqual(len(s["sha256"]),64)
 def test_no_fake_real_boot(self):
  self.a.set_network(kvm=True); self.a.set_vm("Brain-WindowsServer2025","RUNNING")
  r=self.a.readiness(); self.assertTrue(r["ok"]); self.assertNotEqual(r["reality"],"REAL")
if __name__=="__main__": unittest.main()
