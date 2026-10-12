import unittest
from brain_v12.brain.liveness import assess

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

if __name__ == "__main__": unittest.main()
