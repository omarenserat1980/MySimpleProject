import unittest

from brain_v12.brain.ai_gateway import AIGateway


class AIGatewayTests(unittest.TestCase):
    def setUp(self):
        self.gateway = AIGateway()

    def test_unregistered_provider_is_reported(self):
        result = self.gateway.invoke("missing", "text", {"user_text": "hello"})
        self.assertEqual(result, {"ok": False, "error": "PROVIDER_NOT_REGISTERED"})

    def test_unsupported_modality_is_reported(self):
        self.gateway.register("test", ["text"], lambda payload: {"reply": "ok"})
        result = self.gateway.invoke("test", "image", {})
        self.assertEqual(result, {"ok": False, "error": "MODALITY_NOT_SUPPORTED"})

    def test_provider_failure_is_not_reported_as_success(self):
        self.gateway.register("test", ["text"], lambda payload: {"ok": False, "error": "MODEL_OFFLINE"})
        result = self.gateway.invoke("test", "text", {})
        self.assertEqual(result, {"ok": False, "error": "MODEL_OFFLINE", "provider": "test"})

    def test_provider_exception_is_normalized(self):
        def broken(_payload):
            raise RuntimeError("private detail")
        self.gateway.register("test", ["text"], broken)
        result = self.gateway.invoke("test", "text", {})
        self.assertEqual(result["ok"], False)
        self.assertEqual(result["error"], "PROVIDER_INVOCATION_FAILED")
        self.assertEqual(result["provider"], "test")
        self.assertIn("private detail", result["detail"])

    def test_successful_provider_result_is_wrapped(self):
        self.gateway.register("test", ["text"], lambda payload: {"reply": payload["user_text"]})
        result = self.gateway.invoke("test", "text", {"user_text": "hello"})
        self.assertEqual(result, {"ok": True, "provider": "test", "result": {"reply": "hello"}})


if __name__ == "__main__":
    unittest.main()
