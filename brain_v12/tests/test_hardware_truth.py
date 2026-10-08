import unittest, time
from brain_v12.brain.evidence import EvidenceRecord, EvidenceStore
from brain_v12.brain.hardware_reconciler import HardwareReconciler, Observation

class EvidenceTests(unittest.TestCase):
    def test_evidence_is_bound_to_component_and_resource(self):
        e=EvidenceRecord.create(issuer="brain",actor="worker",provider_id="node-a",
          component_id="cpu0",resource_ids=["cpu0:r"],method="probe",source="powershell",
          measurement={"cores":8},ttl_seconds=60)
        s=EvidenceStore(); s.put(e)
        self.assertTrue(s.get_valid(e.evidence_id,"cpu0",["cpu0:r"]).valid())
        with self.assertRaises(RuntimeError):
            s.get_valid(e.evidence_id,"cpu1")

    def test_expired_evidence_rejected(self):
        e=EvidenceRecord.create(issuer="brain",actor="worker",provider_id="node-a",
          component_id="cpu0",resource_ids=["cpu0:r"],method="probe",source="host",
          measurement={"cores":8},ttl_seconds=1)
        s=EvidenceStore(); s.put(e)
        with self.assertRaises(RuntimeError):
            s.get_valid(e.evidence_id)

class ReconcilerTests(unittest.TestCase):
    def test_capacity_drift(self):
        r=HardwareReconciler()
        x=r.compare({"identity":"cpu-a","capacity":{"cores":8},"health":"HEALTHY","attached":True},
          Observation("cpu0","cpu-a",{"cores":4},"HEALTHY",True),observed_at=time.time())
        self.assertEqual(x["drift"],"CAPACITY_DRIFT")
        self.assertIn("REFRESH_RESOURCE_CAPACITY",r.reconcile_plan(x)["actions"])

    def test_identity_drift_quarantines(self):
        r=HardwareReconciler()
        x=r.compare({"identity":"cpu-a","capacity":{"cores":8}},
          Observation("cpu0","cpu-b",{"cores":8},"HEALTHY",False),observed_at=time.time())
        self.assertEqual(x["status"],"QUARANTINE")

    def test_stale_observation_blocks_admission(self):
        r=HardwareReconciler(stale_after_seconds=1)
        x=r.compare({"capacity":{"cores":8}},Observation("cpu0","cpu-a",{"cores":8},"HEALTHY",False),
          observed_at=time.time()-5)
        self.assertEqual(x["drift"],"STALE")

if __name__=="__main__":
    unittest.main()
