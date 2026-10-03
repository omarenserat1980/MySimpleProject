import unittest
from unittest.mock import Mock
from brain_v12.brain.model_router import ModelRouter


class ModelRouterProviderTests(unittest.TestCase):
    def test_routes_to_registered_provider(self):
        provider = Mock(return_value={"ok": True, "result": {"reply": "hello", "model": "test"}})
        router = ModelRouter()
        router.register("test", provider, tasks=["chat"], priority=10)
        result = router.respond("hi")
        self.assertTrue(result["ok"])
        self.assertEqual(result["provider"], "test")
        self.assertEqual(result["reply"], "hello")
        self.assertEqual(result["evidence"]["selected"], "test")

    def test_falls_back_after_provider_failure(self):
        first = Mock(return_value={"ok": False, "error": "TEMPORARY"})
        second = Mock(return_value={"ok": True, "result": {"reply": "fallback", "model": "second"}})
        router = ModelRouter()
        router.register("first", first, tasks=["chat"], priority=10)
        router.register("second", second, tasks=["chat"], priority=20)
        result = router.respond("hi")
        self.assertTrue(result["ok"])
        self.assertEqual(result["provider"], "second")
        self.assertTrue(result["routing"]["fallback_used"])
        self.assertEqual(len(result["evidence"]["attempts"]), 2)

    def test_no_provider_fails_closed(self):
        result = ModelRouter().respond("hi")
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "NO_MODEL_AVAILABLE")


if __name__ == "__main__":
    unittest.main()
