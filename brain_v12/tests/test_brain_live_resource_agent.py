import json
import unittest
from unittest.mock import patch

from brain_v12.tools.brain_live_resource_agent import (
    _validate_base_url,
    collect_resource_snapshot,
    send_heartbeat,
)


class LiveResourceAgentTests(unittest.TestCase):
    def test_snapshot_reports_measured_fields_without_claiming_mining(self):
        result = collect_resource_snapshot()
        self.assertEqual(result["component"], "brain-live-resource-agent")
        self.assertGreaterEqual(result["cpu_logical_count"] or 0, 1)
        self.assertFalse(result["mining_started"])
        self.assertFalse(result["mining_verified"])
        self.assertFalse(result["revenue_verified"])
        self.assertTrue(result["resource_metrics_are_self_reported"])

    def test_remote_plain_http_is_rejected_before_credentials_are_sent(self):
        with self.assertRaisesRegex(ValueError, "REMOTE_BRAIN_URL_REQUIRES_HTTPS"):
            _validate_base_url("http://brain.example.com:8012")

    def test_url_embedded_credentials_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "CREDENTIALS_MUST_NOT_BE_EMBEDDED_IN_URL"):
            _validate_base_url("https://user:secret@brain.example.com")

    def test_heartbeat_requires_matching_server_acknowledgment(self):
        response = {"ok": True, "status": "HEARTBEAT", "agent_id": "node-1"}
        class FakeResponse:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return json.dumps(response).encode()
        with patch("brain_v12.tools.brain_live_resource_agent.urllib.request.urlopen",
                   return_value=FakeResponse()) as open_url:
            result = send_heartbeat("http://127.0.0.1:8012", "node-1", "test-key",
                                    {"component": "test"})
        self.assertTrue(result["heartbeat_acknowledged"])
        self.assertFalse(result["resource_verified"])
        self.assertFalse(result["mining_verified"])
        request = open_url.call_args.args[0]
        self.assertEqual(request.get_header("X-v12-agent-id"), "node-1")
        self.assertEqual(request.get_header("X-v12-agent-key"), "test-key")

    def test_missing_key_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "AGENT_KEY_REQUIRED"):
            send_heartbeat("http://127.0.0.1:8012", "node-1", "", {})


if __name__ == "__main__":
    unittest.main()
