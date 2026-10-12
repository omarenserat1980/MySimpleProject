from __future__ import annotations
import time
import unittest
from threading import Event
from brain_v12.brain.task_worker_pool import ResourceBudget, ResourceGovernor, TaskWorkerPool, WorkerTask

class TaskWorkerPoolTests(unittest.TestCase):
    def test_resource_governor_hard_budget(self):
        g=ResourceGovernor(ResourceBudget(10,10,2))
        a=WorkerTask("a",lambda _:None,cpu_units=8,memory_units=8,weight=2)
        b=WorkerTask("b",lambda _:None,cpu_units=3,memory_units=1,weight=1)
        self.assertTrue(g.try_acquire(a)); self.assertFalse(g.try_acquire(b))
        g.release(a); self.assertTrue(g.try_acquire(b))

    def test_pool_hard_worker_limit_and_completion(self):
        pool=TaskWorkerPool(max_workers=2,queue_limit=10)
        started=Event(); done=Event(); active=0
        def run(_):
            nonlocal active
            active+=1; started.set(); time.sleep(.05); active-=1; done.set()
        pool.start()
        self.assertTrue(pool.submit(WorkerTask("x",run))["ok"])
        self.assertTrue(pool.submit(WorkerTask("y",run))["ok"])
        self.assertFalse(pool.submit(WorkerTask("x",run))["ok"])
        self.assertTrue(done.wait(2))
        pool.shutdown()
        self.assertEqual(pool.snapshot()["worker_count"],2)

    def test_backpressure(self):
        pool=TaskWorkerPool(max_workers=1,queue_limit=1)
        gate=Event()
        pool.start()
        self.assertTrue(pool.submit(WorkerTask("hold",lambda _:gate.wait(2)))["ok"])
        time.sleep(.05)
        self.assertTrue(pool.submit(WorkerTask("queued",lambda _:None))["ok"])
        self.assertFalse(pool.submit(WorkerTask("overflow",lambda _:None))["ok"])
        gate.set(); pool.shutdown()

    def test_failure_is_contained(self):
        pool=TaskWorkerPool(max_workers=1)
        pool.start()
        self.assertTrue(pool.submit(WorkerTask("bad",lambda _: (_ for _ in ()).throw(RuntimeError("boom"))))["ok"])
        time.sleep(.1)
        pool.shutdown()
        self.assertEqual(pool.snapshot()["stats"]["failed"],1)

if __name__=="__main__": unittest.main()
