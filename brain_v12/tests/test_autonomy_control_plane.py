import json, tempfile, unittest
from pathlib import Path
from brain_v12.brain.autonomy_control_plane import ControlPlane

class ControlPlaneTests(unittest.TestCase):
    def test_checkpoint_resume(self):
        with tempfile.TemporaryDirectory() as d:
            cp=ControlPlane(d)
            j=cp.create("film",["plan","render","verify"],max_attempts=3,budget=5)
            j=cp.start_attempt(j)
            j=cp.checkpoint(j,1,{"ok":True})
            self.assertEqual(j["step_index"],1)
            self.assertEqual(j["status"],"ready")

    def test_external_actions_are_gated(self):
        with tempfile.TemporaryDirectory() as d:
            cp=ControlPlane(d)
            j=cp.create("publish",["publish"])
            self.assertEqual(cp.can_run(j,external=True),(False,"external_action_requires_policy_gate"))

    def test_load_reads_latest_persisted_job_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            cp=ControlPlane(d)
            job=cp.create("film",["plan","render"])
            cp.checkpoint(job,1,{"asset":"scene-1"})
            restarted=ControlPlane(d)
            loaded=restarted.load(job["job_id"])
            self.assertEqual(loaded["step_index"],1)
            self.assertEqual(loaded["checkpoint"]["output"],{"asset":"scene-1"})
            self.assertEqual(loaded["status"],"ready")

    def test_restart_recovers_expired_persisted_lease(self):
        with tempfile.TemporaryDirectory() as d:
            cp=ControlPlane(d)
            job=cp.start_attempt(cp.create("build",["compile","verify"]),lease_seconds=30)
            self.assertEqual(job["status"],"running")
            # Simulate the lease expiring while the process is down by updating
            # the latest persisted snapshot, then create a fresh control-plane instance.
            lines=cp.jobs.read_text(encoding="utf-8").splitlines()
            latest=json.loads(lines[-1])
            latest["lease_expires_at"]=0
            lines[-1]=json.dumps(latest,separators=(",",":"))
            cp.jobs.write_text("\n".join(lines)+"\n",encoding="utf-8")

            restarted=ControlPlane(d)
            recovered=restarted.recover_expired_jobs()
            self.assertEqual(len(recovered),1)
            self.assertEqual(recovered[0]["job_id"],job["job_id"])
            self.assertEqual(recovered[0]["status"],"ready")
            self.assertIsNone(recovered[0]["lease_id"])
            persisted=restarted.load(job["job_id"])
            self.assertEqual(persisted["status"],"ready")
            events=[json.loads(line) for line in restarted.events.read_text(encoding="utf-8").splitlines()]
            self.assertTrue(any(e["event"]=="lease_recovered" and e["job_id"]==job["job_id"] for e in events))

if __name__=="__main__": unittest.main()
