import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from fastapi import HTTPException

from brain_v12.brain import render_readonly_api
from brain_v12.brain.render_readonly_connector import (
    RenderConnectorError,
    RenderReadOnlyClient,
    redact,
)


class RenderReadOnlyConnectorTests(unittest.TestCase):
    def setUp(self):
        self.calls = []

    def fake_transport(self, url, headers, timeout):
        self.calls.append((url, headers, timeout))
        return 200, json.dumps({
            "service": {"id": "srv-abc123", "name": "example"},
            "log": "Authorization: Bearer private-value",
        })

    def test_disabled_by_default_makes_no_network_request(self):
        client = RenderReadOnlyClient(transport=self.fake_transport)
        with self.assertRaisesRegex(RenderConnectorError, "disabled"):
            client.service("srv-abc123")
        self.assertEqual(self.calls, [])

    def test_service_uses_fixed_https_api_and_redacts_response(self):
        client = RenderReadOnlyClient(
            enabled=True, api_key="test-key", transport=self.fake_transport,
            policy_check=lambda: True,
        )
        result = client.service("srv-abc123")
        self.assertEqual(len(self.calls), 1)
        url, headers, timeout = self.calls[0]
        self.assertEqual(url, "https://api.render.com/v1/services/srv-abc123")
        self.assertEqual(headers["Authorization"], "Bearer test-key")
        self.assertEqual(timeout, 5.0)
        self.assertEqual(result["log"], "Authorization: [REDACTED] [REDACTED]")

    def test_deploy_list_is_bounded_and_encoded(self):
        client = RenderReadOnlyClient(
            enabled=True, api_key="test-key", transport=self.fake_transport,
            policy_check=lambda: True,
        )
        client.deploys("srv-abc123", limit=7)
        query = parse_qs(urlparse(self.calls[0][0]).query)
        self.assertEqual(query, {"limit": ["7"]})
        with self.assertRaises(ValueError):
            client.deploys("srv-abc123", limit=1000)

    def test_logs_requires_service_id_and_bounded_window(self):
        client = RenderReadOnlyClient(
            enabled=True, api_key="test-key", transport=self.fake_transport,
            policy_check=lambda: True,
        )
        client.logs(
            "srv-abc123", start_time="2026-10-14T00:00:00Z",
            end_time="2026-10-14T01:00:00Z", limit=20,
        )
        query = parse_qs(urlparse(self.calls[0][0]).query)
        self.assertEqual(query["resource"], ["srv-abc123"])
        self.assertEqual(query["limit"], ["20"])
        with self.assertRaises(ValueError):
            client.service("https://attacker.example")
        with self.assertRaises(ValueError):
            client.logs(
                "srv-abc123", start_time="x", end_time="y", limit=5000
            )

    def test_missing_key_fails_before_transport(self):
        client = RenderReadOnlyClient(
            enabled=True, transport=self.fake_transport, policy_check=lambda: True
        )
        with self.assertRaisesRegex(RenderConnectorError, "credential"):
            client.service("srv-abc123")
        self.assertEqual(self.calls, [])

    def test_http_error_body_is_redacted(self):
        def failing_transport(url, headers, timeout):
            return 403, '{"message":"Bearer secret-value","api_key":"secret-key"}'

        client = RenderReadOnlyClient(
            enabled=True, api_key="test-key", transport=failing_transport,
            policy_check=lambda: True,
        )
        with self.assertRaises(RenderConnectorError) as caught:
            client.service("srv-abc123")
        self.assertNotIn("secret-value", str(caught.exception))
        self.assertNotIn("secret-key", str(caught.exception))

    def test_redact_recurses_through_nested_data(self):
        cleaned = redact({
            "access_token": "do-not-show",
            "nested": [{"message": "token=hidden-value"}],
        })
        rendered = json.dumps(cleaned)
        self.assertNotIn("do-not-show", rendered)
        self.assertNotIn("hidden-value", rendered)

    def test_current_repository_policy_blocks_live_requests(self):
        client = RenderReadOnlyClient(
            enabled=True, api_key="test-key", transport=self.fake_transport
        )
        with self.assertRaisesRegex(RenderConnectorError, "policy blocks"):
            client.service("srv-abc123")
        self.assertEqual(self.calls, [])

    def test_explicit_policy_denial_blocks_live_requests(self):
        client = RenderReadOnlyClient(
            enabled=True, api_key="test-key", transport=self.fake_transport,
            policy_check=lambda: False,
        )
        with self.assertRaisesRegex(RenderConnectorError, "policy blocks"):
            client.service("srv-abc123")
        self.assertEqual(self.calls, [])

    def test_timeout_is_bounded(self):
        with self.assertRaises(ValueError):
            RenderReadOnlyClient(timeout=60)


class RenderReadOnlyApiTests(unittest.TestCase):
    def setUp(self):
        self.request = SimpleNamespace(headers={"X-Brain-Control-Key": "control-test"})

    def test_status_reports_policy_block_without_probing(self):
        with patch.dict("os.environ", {"BRAIN_CONTROL_KEY": "control-test"}, clear=False):
            status = render_readonly_api.render_readonly_status(self.request)
        self.assertEqual(status["connection_status"], "NOT_PROBED")
        self.assertFalse(status["policy_allows_external_render"])
        self.assertFalse(status["network_request_made"])
        self.assertFalse(status["write_operations_available"])
        self.assertEqual(status["reason"], "POLICY_BLOCKED")

    def test_status_requires_brain_control_key(self):
        request = SimpleNamespace(headers={})
        with patch.dict("os.environ", {"BRAIN_CONTROL_KEY": "control-test"}, clear=False):
            with self.assertRaises(HTTPException) as caught:
                render_readonly_api.render_readonly_status(request)
        self.assertEqual(caught.exception.status_code, 403)

    def test_service_route_is_fail_closed_when_feature_disabled(self):
        with patch.dict("os.environ", {
            "BRAIN_CONTROL_KEY": "control-test",
            "BRAIN_RENDER_READONLY_ENABLED": "false",
        }, clear=False):
            with self.assertRaises(HTTPException) as caught:
                render_readonly_api.render_readonly_service("srv-abc123", self.request)
        self.assertEqual(caught.exception.status_code, 423)


if __name__ == "__main__":
    unittest.main()
