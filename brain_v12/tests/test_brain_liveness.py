import unittest
from brain_v12.brain.liveness import assess, run_execution_probe


class BrainLivenessTest(unittest.TestCase):
    class Store:
        def __init__(self, state): self._state = state
        def state(self): return self._state
    class Device:
        def __init__(self, payload): self.payload = payload
        def status(self): return self.payload
    class Cognitive:
        STAGES = ("OBSERVE", "DECIDE", "VERIFY")

    def base(self, state=None, configured=True):
        return assess(
            store=self.Store(state or {"status": "READY"}),
            device_bridge=self.Device({"configured": configured, "queued": 0, "pending": 0, "completed": 1, "failed": 0, "agents": {"online": configured, "agents": []}}),
            cognitive=self.Cognitive(),
        )

    def test_alive(self): self.assertEqual(self.base()["status"], "ALIVE")
    def test_degraded_worker(self): self.assertEqual(self.base(configured=False)["status"], "DEGRADED")
    def test_error_core(self): self.assertEqual(self.base({"status": "ERROR"})["status"], "ERROR")
    def test_execution_probe_can_fail(self):
        result = assess(store=self.Store({"status":"READY"}), device_bridge=self.Device({"configured":True,"agents":{"online":True}}), cognitive=self.Cognitive(), probe_result={"ok":False,"status":"PROBE_FAILED"})
        self.assertEqual(result["status"], "DEGRADED")
        self.assertFalse(result["execution_alive"])


class ExecutionProbeVerificationTest(unittest.TestCase):
    class Device:
        def __init__(self, verification):
            self.verification = verification
        def status(self):
            return {"configured": True, "agents": {"online": True}}
        def enqueue(self, task_name, payload):
            return {"ok": True, "task": {"task_id": "probe-1"}}
        def result(self, task_id):
            return {"ok": True, "task": {"task_id": task_id, "status": "COMPLETED", "agent_id": "test-agent"}}
        def verify_result(self, task_id):
            return self.verification

    def test_offline_agent_does_not_enqueue_probe(self):
        class OfflineDevice(self.Device):
            def status(self):
                return {"configured": True, "agents": {"online": False}}
            def enqueue(self, task_name, payload):
                raise AssertionError("must not enqueue when no agent is online")
        result = run_execution_probe(OfflineDevice({"verified": True}))
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "PROBE_AGENT_OFFLINE")

    def test_disabled_bridge_does_not_enqueue_probe(self):
        class DisabledDevice(self.Device):
            def status(self):
                return {"configured": False, "agents": {"online": True}}
            def enqueue(self, task_name, payload):
                raise AssertionError("must not enqueue when the bridge is disabled")
        result = run_execution_probe(DisabledDevice({"verified": True}))
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "PROBE_BRIDGE_DISABLED")

    def test_malformed_agent_status_fails_closed_without_enqueue(self):
        for status in (None, [], "online", {"online": 1}):
            with self.subTest(status=status):
                class MalformedDevice(self.Device):
                    def status(self):
                        return {"configured": True, "agents": status}
                    def enqueue(self, task_name, payload):
                        raise AssertionError("must not enqueue with malformed agent status")
                result = run_execution_probe(MalformedDevice({"verified": True}))
                self.assertFalse(result["ok"])
                self.assertEqual(result["status"], "PROBE_AGENT_OFFLINE")

    def test_missing_verification_fails_closed(self):
        result = run_execution_probe(self.Device({}))
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "PROBE_VERIFICATION_FAILED")

    def test_explicit_true_verification_passes(self):
        result = run_execution_probe(self.Device({"verified": True}))
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "PROBE_COMPLETED")

    def test_false_verification_fails_closed(self):
        result = run_execution_probe(self.Device({"verified": False}))
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "PROBE_VERIFICATION_FAILED")

    def test_malformed_verification_fails_closed(self):
        for payload in (None, [], "verified"):
            with self.subTest(payload=payload):
                result = run_execution_probe(self.Device(payload))
                self.assertFalse(result["ok"])
                self.assertEqual(result["status"], "PROBE_VERIFICATION_FAILED")
                self.assertFalse(result["verification"]["verified"])


if __name__ == "__main__": unittest.main()
