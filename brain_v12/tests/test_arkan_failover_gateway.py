import tempfile
import unittest
from pathlib import Path
from brain_v12.brain.arkan_failover_gateway import ArkanFailoverGateway
from brain_v12.brain.digital_twin_fabric import RealityGate, Reality

def real_evidence():
    return {"device_id":"d0f5f0a0-f105-4750-8254-cca35dfe9c29","heartbeat_at":"2026-10-09T09:00:00+03:00",
            "task_id":"t-real","task_evidence":True,"verification":"VERIFIED","heartbeat":"FRESH","reality":"REAL","source":"desktop-commander"}

class TestArkanFailoverGateway(unittest.TestCase):
    def test_virtual_when_real_missing(self):
        with tempfile.TemporaryDirectory() as d:
            g=ArkanFailoverGateway(Path(d))
            s=g.connect()
            self.assertEqual(s["mode"],"VIRTUAL")
            self.assertEqual(s["reality"],"SIMULATED")
            r=g.run_powershell("Write-Output hello; Get-ComputerInfo")
            self.assertTrue(r["ok"])
            self.assertIn("hello",r["output"])

    def test_real_selected_only_after_validation(self):
        with tempfile.TemporaryDirectory() as d:
            g=ArkanFailoverGateway(Path(d),real_probe=real_evidence)
            s=g.connect()
            self.assertEqual(s["mode"],"REAL")
            self.assertEqual(g.heartbeat()["reality"],"REAL")

    def test_invalid_real_falls_back(self):
        with tempfile.TemporaryDirectory() as d:
            bad=lambda: {"reality":"SIMULATED","heartbeat":"FRESH","task_evidence":True,"verification":"VERIFIED",
                         "device_id":"x","heartbeat_at":"now","task_id":"t"}
            g=ArkanFailoverGateway(Path(d),real_probe=bad)
            self.assertEqual(g.connect()["mode"],"VIRTUAL")

    def test_virtual_never_proves_real(self):
        with tempfile.TemporaryDirectory() as d:
            g=ArkanFailoverGateway(Path(d))
            g.connect()
            evidence={"reality":"SIMULATED","source":"digital-twin"}
            self.assertFalse(RealityGate.accept(evidence,Reality.REAL)["ok"])

    def test_recovery_switches_back_to_real(self):
        with tempfile.TemporaryDirectory() as d:
            state={"up":False}
            def probe():
                if not state["up"]: raise RuntimeError("offline")
                return real_evidence()
            g=ArkanFailoverGateway(Path(d),real_probe=probe)
            self.assertEqual(g.connect()["mode"],"VIRTUAL")
            state["up"]=True
            self.assertEqual(g.recover_real()["mode"],"REAL")

if __name__=="__main__":
    unittest.main(verbosity=2)
