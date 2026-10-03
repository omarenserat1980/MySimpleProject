import unittest
from unittest.mock import patch

from brain_v12.brain.model_providers import GeminiModelProvider, OllamaModelProvider, OpenAIModelProvider, configured_model_providers


class ModelProviderTests(unittest.TestCase):
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key", "OPENAI_MODEL": "test-model"}, clear=False)
    @patch("brain_v12.brain.model_providers.httpx.Client")
    def test_openai_provider_uses_server_secret(self, client_cls):
        client_cls.return_value.__enter__.return_value.post.return_value.status_code = 200
        client_cls.return_value.__enter__.return_value.post.return_value.json.return_value = {
            "id": "resp-1", "output_text": "hello"
        }
        result = OpenAIModelProvider().respond("hi")
        self.assertTrue(result["ok"])
        self.assertEqual(result["result"]["reply"], "hello")
        _, kwargs = client_cls.return_value.__enter__.return_value.post.call_args
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")

    @patch.dict("os.environ", {"GEMINI_API_KEY": "gem-key", "GEMINI_MODEL": "gem-model"}, clear=False)
    @patch("brain_v12.brain.model_providers.httpx.Client")
    def test_gemini_provider(self, client_cls):
        client_cls.return_value.__enter__.return_value.post.return_value.status_code = 200
        client_cls.return_value.__enter__.return_value.post.return_value.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "gemini reply"}]}}]
        }
        result = GeminiModelProvider().respond("hi")
        self.assertTrue(result["ok"])
        self.assertEqual(result["result"]["reply"], "gemini reply")

    @patch.dict("os.environ", {"OLLAMA_ENABLED": "1", "OLLAMA_MODEL": "local-test"}, clear=False)
    @patch("brain_v12.brain.model_providers.httpx.Client")
    def test_ollama_provider(self, client_cls):
        client_cls.return_value.__enter__.return_value.post.return_value.status_code = 200
        client_cls.return_value.__enter__.return_value.post.return_value.json.return_value = {"response": "local reply"}
        result = OllamaModelProvider().respond("hi")
        self.assertTrue(result["ok"])
        self.assertEqual(result["result"]["reply"], "local reply")

    @patch.dict("os.environ", {"OPENAI_API_KEY": "", "GEMINI_API_KEY": "", "OLLAMA_ENABLED": "0"}, clear=False)
    def test_factory_fail_closed_without_provider(self):
        self.assertEqual(configured_model_providers(), [])


if __name__ == "__main__":
    unittest.main()
