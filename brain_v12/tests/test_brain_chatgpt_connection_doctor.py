import unittest
from unittest.mock import patch

from brain_v12.tools.brain_chatgpt_connection_doctor import (
    resolve_origin, validate_origin, run,
)


class ConnectionDoctorTests(unittest.TestCase):
    def test_missing_origin_is_explicit_blocker(self):
        self.assertEqual(validate_origin(""), "API_ORIGIN_MISSING")
        self.assertEqual(run("")["blocker"], "API_ORIGIN_MISSING")

    def test_rejects_plain_http_public_host(self):
        self.assertIn("MUST_BE_HTTPS", validate_origin("http://example.com"))

    def test_allows_loopback_http_for_local_development(self):
        self.assertIsNone(validate_origin("http://127.0.0.1:8012"))

    def test_rejects_credentials_in_url(self):
        self.assertEqual(validate_origin("https://user:pass@example.com"), "API_ORIGIN_INVALID")

    def test_resolves_configured_environment_without_printing_it(self):
        with patch.dict("os.environ", {"BRAIN_API_ORIGIN": "https://brain.example.org/"}):
            self.assertEqual(resolve_origin(None), "https://brain.example.org")

    @patch("brain_v12.tools.brain_chatgpt_connection_doctor.request_json")
    def test_success_requires_all_three_live_probes(self, request_json):
        request_json.side_effect = [
            {"ok": True, "status": 200, "json": {"ok": True}},
            {"ok": True, "status": 200, "json": {"ok": True, "available": True, "provider": {"configured": True}, "model_router": {"providers": ["local"]}}},
            {"ok": True, "status": 200, "json": {"ok": True, "sessions": []}},
        ]
        report = run("https://brain.example.org")
        self.assertTrue(report["success"])
        self.assertEqual(request_json.call_count, 3)

    @patch("brain_v12.tools.brain_chatgpt_connection_doctor.request_json")
    def test_ai_status_unavailable_fails_closed(self, request_json):
        request_json.side_effect = [
            {"ok": True, "status": 200, "json": {"ok": True}},
            {"ok": True, "status": 200, "json": {"ok": False, "available": False}},
            {"ok": True, "status": 200, "json": {"ok": True, "sessions": []}},
        ]
        report = run("https://brain.example.org")
        self.assertFalse(report["success"])
        self.assertEqual(report["blocker"], "ONE_OR_MORE_API_PROBES_FAILED")

    @patch("brain_v12.tools.brain_chatgpt_connection_doctor.request_json")
    def test_no_model_provider_fails_closed(self, request_json):
        request_json.side_effect = [
            {"ok": True, "status": 200, "json": {"ok": True}},
            {"ok": True, "status": 200, "json": {
                "ok": True, "provider": {"configured": False}, "model_router": {"providers": []}
            }},
            {"ok": True, "status": 200, "json": {"ok": True, "sessions": []}},
        ]
        report = run("https://brain.example.org")
        self.assertFalse(report["success"])
        self.assertEqual(report["blocker"], "ONE_OR_MORE_API_PROBES_FAILED")
        self.assertEqual(report["checks"]["brain_ai_status"]["error"], "NO_MODEL_PROVIDER_CONFIGURED")

    @patch("brain_v12.tools.brain_chatgpt_connection_doctor.request_json")
    def test_live_chat_test_is_opt_in_and_safe_mode(self, request_json):
        request_json.side_effect = [
            {"ok": True, "status": 200, "json": {"ok": True}},
            {"ok": True, "status": 200, "json": {"ok": True, "provider": {"configured": True}, "model_router": {"providers": ["local"]}}},
            {"ok": True, "status": 200, "json": {"ok": True, "sessions": []}},
            {"ok": True, "status": 200, "json": {"ok": True, "session": {"id": "s-1"}}},
            {"ok": True, "status": 200, "json": {"ok": True, "response": {"content": "BRAIN_CHAT_CONNECTION_OK"}}},
        ]
        report = run("https://brain.example.org", send_test_message=True)
        self.assertTrue(report["success"])
        self.assertTrue(report["chat_test"]["message"]["reply_marker_match"])
        self.assertEqual(request_json.call_args_list[-1].kwargs["payload"]["approved"], False)


if __name__ == "__main__":
    unittest.main()
