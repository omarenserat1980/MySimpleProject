import io
import json
import unittest
from unittest.mock import patch

from tools.windows_control_plane_api_preflight import inspect_openapi, ISSUE_PATH


class FakeResponse:
    status = 200
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return self.payload


class ControlPlaneApiPreflightTests(unittest.TestCase):
    def test_gets_only_openapi_and_confirms_post_route_without_calling_it(self):
        seen = []
        def opener(request, timeout):
            seen.append((request.get_method(), request.full_url, timeout))
            return FakeResponse({"paths": {ISSUE_PATH: {"post": {"summary": "issue"}}}})
        result = inspect_openapi("https://control.example", opener=opener)
        self.assertTrue(result["ok"])
        self.assertTrue(result["contract_issuance_route_published"])
        self.assertFalse(result["issuance_endpoint_called"])
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0][0], "GET")
        self.assertEqual(seen[0][1], "https://control.example/openapi.json")

    def test_missing_route_blocks(self):
        result = inspect_openapi("https://control.example", opener=lambda *a, **k: FakeResponse({"paths": {}}))
        self.assertFalse(result["ok"])
        self.assertIn("CONTRACT_ISSUANCE_POST_ROUTE_NOT_PUBLISHED", result["blockers"])

    def test_rejects_http_and_embedded_credentials_without_network(self):
        for url in ("http://control.example", "https://user:pass@control.example"):
            result = inspect_openapi(url, opener=lambda *a, **k: self.fail("network must not be called"))
            self.assertFalse(result["ok"])
            self.assertEqual(result["blockers"], ["CONTROL_PLANE_HTTPS_URL_INVALID"])

    def test_unreachable_is_sanitized(self):
        import urllib.error
        result = inspect_openapi("https://control.example", opener=lambda *a, **k: (_ for _ in ()).throw(urllib.error.URLError("private detail")))
        self.assertFalse(result["ok"])
        self.assertEqual(result["blockers"], ["CONTROL_PLANE_UNREACHABLE"])
        self.assertNotIn("private detail", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
