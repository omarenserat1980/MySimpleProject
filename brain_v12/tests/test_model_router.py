import unittest

from brain_v12.brain.model_router import ModelRouter

class FakeProvider:
    def __init__(self, name, ok=True): self.name, self.ok = name, ok
    def status(self): return {"provider": self.name, "model": "test", "configured": True}
    def respond(self, user_text, context="", instructions=""):
        return {"ok": self.ok, "provider": self.name, "model": "test", "reply": f"{self.name}:{user_text}", "error": None if self.ok else "FAILED"}

class TestModelRouter(unittest.TestCase):
    def test_default_route(self):
        r=ModelRouter(); r.register("primary",FakeProvider("primary"),default=True)
        self.assertEqual(r.route("hello").provider_name,"primary")
    def test_capability_route(self):
        r=ModelRouter(); r.register("text",FakeProvider("text"),default=True); r.register("vision",FakeProvider("vision"),capabilities=["multimodal"])
        result=r.respond("أريد صورة",requested_capability="multimodal")
        self.assertTrue(result["ok"]); self.assertEqual(result["provider"],"vision")
    def test_fallback(self):
        r=ModelRouter(); r.register("primary",FakeProvider("primary",False),default=True); r.register("backup",FakeProvider("backup"))
        result=r.respond("hello")
        self.assertTrue(result["ok"]); self.assertEqual(result["provider"],"backup"); self.assertEqual(result["route_reason"],"fallback")
        self.assertTrue(result["fallback_errors"])

if __name__ == "__main__": unittest.main()
