import unittest
from brain_v12.brain.capability_fabric import CapabilityFabric, ExecutorSpec

class CapabilityFabricTests(unittest.TestCase):
    def test_fallback(self):
        fabric=CapabilityFabric()
        fabric.register(ExecutorSpec("local","video.render",priority=10,cost_class="FREE"))
        fabric.register(ExecutorSpec("paid","video.render",priority=30,cost_class="PAID"))
        calls=[]
        def runner(spec):
            calls.append(spec.executor_id)
            if spec.executor_id=="local": raise RuntimeError("unavailable")
            return {"artifact":"ok"}
        result=fabric.execute("video.render",runner,max_attempts=2)
        self.assertEqual(result["status"],"SUCCESS")
        self.assertEqual(result["executor_id"],"paid")
        self.assertEqual(calls,["local","paid"])

    def test_permission_filter(self):
        fabric=CapabilityFabric()
        fabric.register(ExecutorSpec("safe","publish",priority=10))
        fabric.register(ExecutorSpec("oauth","publish",priority=20,permissions=frozenset({"youtube.upload"})))
        self.assertEqual([x.executor_id for x in fabric.plan("publish",{"youtube.upload"})],["oauth"])

    def test_missing_capability_is_failure(self):
        result=CapabilityFabric().execute("missing",lambda _: True)
        self.assertEqual(result["status"],"FAILED")
        self.assertEqual(result["attempts"],[])

if __name__=="__main__": unittest.main()
