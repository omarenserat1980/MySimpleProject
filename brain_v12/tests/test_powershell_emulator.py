import tempfile,unittest
from brain_v12.brain.desktop_commander_emulator import DesktopCommanderEmulator
from brain_v12.brain.powershell_emulator import PowerShellEmulator

class PowerShellEmulatorTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.d=DesktopCommanderEmulator(self.tmp.name)
  self.ps=PowerShellEmulator(self.d)
 def tearDown(self): self.tmp.cleanup()
 def test_info(self):
  self.assertEqual(self.ps.info()["mode"],"SIMULATED")
 def test_filesystem_commands(self):
  r=self.ps.run('New-Item test.txt; Set-Content test.txt -Value "hello"; Get-Content test.txt')
  self.assertTrue(r["ok"]); self.assertIn("hello",r["output"])
 def test_location_and_listing(self):
  self.assertTrue(self.ps.run("New-Item -ItemType Directory data; Set-Location data")["ok"])
  self.assertIn("data",self.ps.run("Set-Location ..; Get-ChildItem")["output"])
 def test_process_is_simulated(self):
  r=self.ps.run("Get-Process; Get-ComputerInfo")
  self.assertTrue(r["ok"]); self.assertIn("SIMULATED",r["output"])
 def test_unsupported_fails_closed(self):
  r=self.ps.run("Invoke-Expression 'whoami'")
  self.assertFalse(r["ok"]); self.assertEqual(r["errors"][0]["status"],"COMMAND_NOT_SUPPORTED")
 def test_command_limit(self):
  p=PowerShellEmulator(self.d,policy=type("P",(),{"max_commands":1,"max_output_bytes":65536,"allow_mutation":True})())
  self.assertFalse(p.run("Write-Output a; Write-Output b")["ok"])
if __name__=="__main__": unittest.main()
