import unittest
from types import SimpleNamespace

from brain_v12.brain.supervisor import BrainSupervisor


class FakeStore:
    def __init__(self):
        self.events = []
    def event(self, name, payload):
        self.events.append((name, payload))


class FakeBridge:
    def status(self):
        return {"agents": []}
    def agent_status(self):
        return {"agents": []}
    def enqueue(self, task, params):
        return {"ok": True, "task": {"task_id": "t1"}}


class OfflineGateway:
    def authorize(self, capability):
        raise RuntimeError("BRAIN_INTERNAL_RUNNER_NOT_VERIFIED")


class OnlineGateway:
    def authorize(self, capability):
        return SimpleNamespace(executor="brain-internal", verified=True)


class SupervisorAuthorityTests(unittest.TestCase):
    def test_submit_fails_closed_without_internal_authority(self):
        s = BrainSupervisor(FakeStore(), FakeBridge(), execution_gateway=OfflineGateway())
        r = s.submit("build")
        self.assertFalse(r["ok"])
        self.assertEqual(r["status"], "BLOCKED_NO_INTERNAL_EXECUTOR")

    def test_submit_records_internal_authority(self):
        store = FakeStore()
        s = BrainSupervisor(store, FakeBridge(), execution_gateway=OnlineGateway())
        r = s.submit("build")
        self.assertTrue(r["ok"])
        self.assertEqual(store.events[-1][1]["execution_authority"], "brain-internal")
        self.assertTrue(store.events[-1][1]["execution_authority_verified"])


if __name__ == "__main__":
    unittest.main()
