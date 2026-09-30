import tempfile,unittest
from brain_v12.brain.job_dispatcher import JobDispatcher

class DispatcherTests(unittest.TestCase):
    def test_full_lifecycle(self):
        with tempfile.TemporaryDirectory() as d:
            x=JobDispatcher(d)
            j=x.plan(x.create("probe",["python"]))
            w={"worker_id":"w1","capabilities":["python"],"status":"healthy"}
            j=x.start(x.acquire(j,w))
            j=x.verify(j,{"verified":True,"artifact":"ok"})
            self.assertEqual(x.release(j)["status"],"RELEASED")
    def test_capability_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            x=JobDispatcher(d); j=x.plan(x.create("film",["ffmpeg"]))
            self.assertIsNone(x.select_worker(j,[{"worker_id":"w1","capabilities":["python"],"status":"healthy"}]))
    def test_failed_job_retries_then_fails(self):
        with tempfile.TemporaryDirectory() as d:
            x=JobDispatcher(d,max_attempts=2); j=x.plan(x.create("x",["python"]))
            w={"worker_id":"w1","capabilities":["python"],"status":"healthy"}
            j=x.start(x.acquire(j,w)); j=x.fail(j,"test"); self.assertEqual(j["status"],"RETRYING")
            j=x.acquire(j,w); j=x.start(j); j=x.fail(j,"test"); self.assertEqual(j["status"],"FAILED")
