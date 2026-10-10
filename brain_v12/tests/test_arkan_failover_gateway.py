import tempfile
import unittest
from pathlib import Path
from brain_v12.brain.arkan_failover_gateway import ArkanFailoverGateway
from brain_v12.brain.digital_twin_fabric import RealityGate, Reality

def real_evidence():
    return {"device_id":"d0f5f0a0-f105-4750-8254-cca35dfe9c29","heartbeat_at":"2026-10-10T09:00:00+03:00",
            "task_id":"t-real","task_evidence":True,"verification":"VERIFIED","heartbeat":"FRESH","reality":"REAL","source":"desktop-commander"}

class TestArkanFailoverGateway(unittest.TestCase):
    def test_simulation_is_default_even_when_real_probe_exists(self):
        calls = []
        def probe():
            calls.append(True)
            return real_evidence()
        with tempfile.TemporaryDirectory() as d:
            g=ArkanFailoverGateway(Path(d),real_probe=probe)
            s=g.connect()
            self.assertEqual(s["mode"],"VIRTUAL")
            self.assertEqual(s["reality"],"SIMULATED")
            self.assertEqual(s["policy"],"SIMULATION_FIRST")
            self.assertEqual(calls, [])
            r=g.run_powershell("Write-Output hello; Get-ComputerInfo")
            self.assertTrue(r["ok"])
            self.assertIn("hello",r["output"])

    def test_real_promotion_requires_explicit_recovery_and_validation(self):
        with tempfile.TemporaryDirectory() as d:
            g=ArkanFailoverGateway(Path(d),real_probe=real_evidence)
            self.assertEqual(g.connect()["mode"],"VIRTUAL")
            s=g.recover_real()
            self.assertEqual(s["mode"],"REAL")
            self.assertEqual(s["reality"],"REAL")
            self.assertEqual(g.heartbeat()["reality"],"REAL")

    def test_real_first_is_only_enabled_by_explicit_policy(self):
        with tempfile.TemporaryDirectory() as d:
            g=ArkanFailoverGateway(Path(d),real_probe=real_evidence,prefer_real=True)
            s=g.connect()
            self.assertEqual(s["mode"],"REAL")
            self.assertEqual(s["policy"],"REAL_FIRST")

    def test_invalid_real_evidence_falls_back(self):
        with tempfile.TemporaryDirectory() as d:
            bad=lambda: {"reality":"SIMULATED","heartbeat":"FRESH","task_evidence":True,"verification":"VERIFIED",
                         "device_id":"x","heartbeat_at":"now","task_id":"t"}
            g=ArkanFailoverGateway(Path(d),real_probe=bad,prefer_real=True)
            self.assertEqual(g.connect()["mode"],"VIRTUAL")

    def test_virtual_never_proves_real(self):
        with tempfile.TemporaryDirectory() as d:
            g=ArkanFailoverGateway(Path(d))
            g.connect()
            evidence={"reality":"SIMULATED","source":"digital-twin"}
            self.assertFalse(RealityGate.accept(evidence,Reality.REAL)["ok"])

    def test_recovery_switches_to_real_only_after_fresh_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            state={"up":False}
            def probe():
                if not state["up"]: raise RuntimeError("offline")
                return real_evidence()
            g=ArkanFailoverGateway(Path(d),real_probe=probe)
            self.assertEqual(g.connect()["mode"],"VIRTUAL")
            self.assertEqual(g.recover_real()["mode"],"VIRTUAL")
            state["up"]=True
            self.assertEqual(g.recover_real()["mode"],"REAL")

if __name__=="__main__":
    unittest.main(verbosity=2)
