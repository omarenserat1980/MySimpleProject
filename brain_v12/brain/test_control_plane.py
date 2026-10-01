import tempfile,unittest
from .autonomy_control_plane import ControlPlane
class ControlPlaneTests(unittest.TestCase):
    def test_idempotency_and_lease_recovery(self):
        with tempfile.TemporaryDirectory() as d:
            c=ControlPlane(d); a=c.create("x",["execute"],idempotency_key="same"); b=c.create("x",["execute"],idempotency_key="same"); self.assertEqual(a["job_id"],b["job_id"])
            j=c.start_attempt(a,lease_seconds=1); j["lease_expires_at"]=0; r=c.recover_expired(j); self.assertEqual(r["status"],"ready")
            events=(c.events.read_text()).splitlines(); self.assertTrue(events); self.assertIn("digest",events[-1]); self.assertIn("prev",events[-1])
if __name__=="__main__": unittest.main()
