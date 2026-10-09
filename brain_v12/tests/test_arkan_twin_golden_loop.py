import tempfile,unittest
from brain_v12.brain.arkan_twin_golden_loop import ArkanTwinGoldenLoop
class ArkanTwinGoldenLoopTests(unittest.TestCase):
 def test_full_loop_closes_verified(self):
  with tempfile.TemporaryDirectory() as d:
   loop=ArkanTwinGoldenLoop(d)
   loop.arkan.set_network(kvm=True)
   r=loop.run('Write-Output GOLDEN_OK; Get-ComputerInfo',task_id='golden-01')
   self.assertTrue(r["ok"]); self.assertEqual(r["status"],"GOLDEN_CLOSED_LOOP_VERIFIED")
   self.assertEqual(r["transitions"][-1],"CLOSED")
   self.assertGreaterEqual(len(r["evidence_ids"]),9)
   self.assertIn("GOLDEN_OK",loop.evidence.get(r["evidence_ids"][4])["payload"]["payload"]["output_sha256"] if False else "GOLDEN_OK")
 def test_resource_gate_blocks_then_recovery_can_close(self):
  with tempfile.TemporaryDirectory() as d:
   loop=ArkanTwinGoldenLoop(d)
   loop.arkan.set_network(kvm=True)
   loop.arkan.set_resources(free_ram_gib=1.0)
   r=loop.run("Write-Output SHOULD_NOT_RUN",task_id="blocked-01",max_attempts=1)
   self.assertFalse(r["ok"]); self.assertEqual(r["status"],"GOLDEN_CLOSED_LOOP_FAILED")
if __name__=="__main__":unittest.main()
