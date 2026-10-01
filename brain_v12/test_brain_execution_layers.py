import unittest
from .brain.capability_registry import CapabilityRegistry
from .brain.failure_policy import FailurePolicy
from .blade_server import BladeChassis
from .brain.executor_adapter import BladeExecutorAdapter

class ExecutionLayerTests(unittest.TestCase):
    def test_capability_selection_is_identity_agnostic(self):
        r=CapabilityRegistry()
        r.register("phone-a",{"cpu","ram"})
        r.register("server-b",{"cpu","ram","gpu"})
        self.assertEqual([x.executor_id for x in r.select({"gpu"})],["server-b"])

    def test_failure_policy_is_bounded(self):
        p=FailurePolicy()
        d=p.decide("QEMU_NOT_AVAILABLE",1,3)
        self.assertTrue(d.retryable)
        self.assertGreater(d.delay_seconds,0)
        self.assertEqual(p.decide("POLICY_BLOCKED",1,3).retryable,False)
        self.assertEqual(p.decide("TIMEOUT",3,3).retryable,False)

    def test_blade_executor_adapter(self):
        c=BladeChassis()
        b=c.create_blade({"cpu"})
        b.power_on()
        result=BladeExecutorAdapter(b).execute(type("T",(),{"program":[("HALT",)],"max_cycles":10})())
        self.assertTrue(result.ok)
        self.assertEqual(result.status,"COMPLETED")

if __name__=="__main__":
    unittest.main()
