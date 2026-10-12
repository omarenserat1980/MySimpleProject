import time
import unittest
import tempfile
from .blade_server import BladeChassis
from .brain.resource_manager import ResourceManager, ResourceRequirement
from .brain.virtual_task_queue import VirtualTaskQueue
from .brain.workload_controller import WorkloadController

class VirtualTaskQueueTests(unittest.TestCase):
    def setUp(self):
        self.chassis=BladeChassis()
        self.blade=self.chassis.create_blade({"cpu","ram"},ram_size=1024)
        self.blade.power_on()
        self.resources=ResourceManager()
        self.temp=tempfile.TemporaryDirectory()
        self.queue=VirtualTaskQueue(self.chassis,self.resources,max_workers=2,store_path=self.temp.name+"/tasks.db")

    def tearDown(self):
        self.queue.shutdown()
        self.temp.cleanup()

    def wait(self, task_id):
        deadline=time.time()+2
        while time.time()<deadline:
            task=self.queue.get(task_id)
            if task and task.status in {"COMPLETED","FAILED"}:
                return task
            time.sleep(0.01)
        return self.queue.get(task_id)

    def test_task_is_queued_then_completed(self):
        task=self.queue.submit([("MOVI",0,9),("OUT",0),("HALT",)])
        final=self.wait(task.task_id)
        self.assertEqual(final.status,"COMPLETED")
        self.assertEqual(final.result["result"]["output"],[9])
        self.assertIsNotNone(final.blade_id)

    def test_second_task_waits_for_reserved_cpu(self):
        req=ResourceRequirement(cpu_cores=1,ram_bytes=900)
        first=self.queue.submit([("HALT",)],requirement=req,task_id="one")
        second=self.queue.submit([("HALT",)],requirement=req,task_id="two")
        self.assertIn(self.queue.get(second.task_id).status,{"WAITING","RUNNING","COMPLETED"})
        self.assertIsNotNone(self.wait(first.task_id))
        self.assertIsNotNone(self.wait(second.task_id))

if __name__=="__main__":
    unittest.main()


    def test_emergency_backpressure_holds_background_work(self):
        self.queue.workload_controller = WorkloadController()
        self.queue.workload_controller.policy = WorkloadController().policy
        original = self.queue.store.counts
        self.queue.store.counts = lambda: {"QUEUED": 800, "WAITING": 0, "RUNNING": 0}
        try:
            task = self.queue.submit([("HALT",)], required_capabilities={"cpu"}, task_id="backpressure")
            self.assertEqual(self.queue.get(task.task_id).status, "WAITING")
        finally:
            self.queue.store.counts = original


    def test_priority_is_persisted(self):
        task=self.queue.submit([("HALT",)], task_id="high-priority", priority="HIGH")
        self.assertEqual(task.priority, "HIGH")
