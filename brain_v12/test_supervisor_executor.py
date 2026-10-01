import tempfile, unittest
from .blade_server import BladeChassis
from .brain.resource_manager import ResourceManager
from .brain.virtual_task_queue import VirtualTaskQueue
from .brain.brain_supervisor import BrainSupervisor
from .brain.supervisor_executor import SupervisorExecutor

class SupervisorExecutorTests(unittest.TestCase):
    def test_submit_and_inspect(self):
        c=BladeChassis()
        b=c.create_blade({"cpu"}); b.power_on()
        q=VirtualTaskQueue(c,ResourceManager(),store_path=tempfile.mktemp())
        x=SupervisorExecutor(BrainSupervisor(root=tempfile.mkdtemp()),q)
        task=x.submit([("HALT",)])
        self.assertTrue(task["ok"])
        q.shutdown()

if __name__=="__main__":
    unittest.main()
