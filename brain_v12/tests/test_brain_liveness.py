import unittest

from brain_v12.brain.liveness import assess


class BrainLivenessTest(unittest.TestCase):
    class Store:
        def __init__(self, state):
            self._state = state
        def state(self):
            return self._state

    class Device:
        def __init__(self, payload):
            self.payload = payload
        def status(self):
            return self.payload

    class Cognitive:
        STAGES = ("OBSERVE", "DECIDE", "VERIFY")

    def test_alive_when_core_and_bridge_are_healthy(self):
        result = assess(
            store=self.Store({"status": "READY", "cognitive_stage": "READY"}),
            device_bridge=self.Device({
                "configured": True,
                "queued": 0,
                "pending": 0,
                "completed": 1,
                "failed": 0,
                "agents": {"online": True, "agents": []},
            }),
            cognitive=self.Cognitive(),
        )
        self.assertTrue(result["brain_alive"])
        self.assertEqual(result["status"], "ALIVE")

    def test_degraded_when_optional_bridge_is_down(self):
        result = assess(
            store=self.Store({"status": "READY"}),
            device_bridge=self.Device({
                "configured": False,
                "agents": {"online": False, "agents": []},
            }),
            cognitive=self.Cognitive(),
        )
        self.assertTrue(result["brain_alive"])
        self.assertEqual(result["status"], "DEGRADED")

    def test_error_when_core_runtime_is_in_error(self):
        result = assess(
            store=self.Store({"status": "ERROR"}),
            device_bridge=self.Device({"configured": True, "agents": {"online": True}}),
            cognitive=self.Cognitive(),
        )
        self.assertFalse(result["brain_alive"])
        self.assertEqual(result["status"], "ERROR")


if __name__ == "__main__":
    unittest.main()
