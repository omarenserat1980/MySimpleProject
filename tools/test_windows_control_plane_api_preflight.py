import contextlib
import io
import json
import os
import unittest
import urllib.error
from unittest.mock import patch

from tools.windows_control_plane_api_preflight import inspect_openapi, ISSUE_PATH, main, DEFAULT_CONTROL_PLANE_URL


class FakeResponse:
    status = 200
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return self.payload


class ControlPlaneApiPreflightTests(unittest.TestCase):
    def test_main_uses_public_https_default_when_env_is_unset(self):
        expected = {"ok": True, "status": "READ_ONLY_API_READY"}
        with patch.dict(os.environ, {}, clear=True), patch("tools.windows_control_plane_api_preflight.inspect_openapi", return_value=expected) as probe:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(), 0)
        probe.assert_called_once_with(DEFAULT_CONTROL_PLANE_URL)
        self.assertEqual(json.loads(output.getvalue()), expected)

    def test_reads_openapi_and_never_calls_issuance(self):
        seen = []
        def opener(request, timeout):
            seen.append((request.get_method(), request.full_url))
            return FakeResponse({"paths": {ISSUE_PATH: {"post": {"summary": "issue"}}}})
        result = inspect_openapi("https://control.example", opener=opener)
        self.assertTrue(result["ok"])
        self.assertEqual(seen, [("GET", "https://control.example/openapi.json")])
        self.assertFalse(result["issuance_endpoint_called"])

    def test_missing_issuance_route_blocks(self):
        result = inspect_openapi("https://control.example", opener=lambda *a, **k: FakeResponse({"paths": {}}))
        self.assertFalse(result["ok"])
        self.assertIn("CONTRACT_ISSUANCE_POST_ROUTE_NOT_PUBLISHED", result["blockers"])

    def test_rejects_insecure_or_credential_bearing_urls_without_network(self):
        for url in ("http://control.example", "https://user:pass@control.example", "not a url"):
            result = inspect_openapi(url, opener=lambda *a, **k: self.fail("network must not be called"))
            self.assertFalse(result["ok"])
            self.assertEqual(result["blockers"], ["CONTROL_PLANE_HTTPS_URL_INVALID"])

    def test_network_errors_are_sanitized(self):
        def fail(*args, **kwargs):
            raise urllib.error.URLError("sensitive private detail")
        result = inspect_openapi("https://control.example", opener=fail)
        self.assertFalse(result["ok"])
        self.assertEqual(result["blockers"], ["CONTROL_PLANE_UNREACHABLE"])
        self.assertNotIn("sensitive private detail", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
