import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from tools.request_cloud_executor_attestation import _safe_http_error, post


class CloudExecutorAttestationClientTests(unittest.TestCase):
    def test_http_auth_error_is_reported_without_response_dump(self):
        body = json.dumps({"detail": "CLOUD_EXECUTOR_AUTH_REJECTED"}).encode()
        error = HTTPError("https://example.invalid/attestation/challenge", 403, "Forbidden", {}, io.BytesIO(body))
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaisesRegex(RuntimeError, r"CLOUD_EXECUTOR_HTTP_403:CLOUD_EXECUTOR_AUTH_REJECTED"):
                post("https://example.invalid", "/api/cloud-executor/attestation/challenge", "not-a-real-token", {"executor_id": "test-executor"})

    def test_untrusted_error_text_is_not_echoed(self):
        secret_like = "token-should-not-appear"
        body = json.dumps({"detail": secret_like}).encode()
        error = HTTPError("https://example.invalid/path", 403, "Forbidden", {}, io.BytesIO(body))
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(RuntimeError) as ctx:
                post("https://example.invalid", "/path", "never-print-this", {"executor_id": "test"})
        self.assertNotIn("never-print-this", str(ctx.exception))
        self.assertNotIn(secret_like, str(ctx.exception))
        self.assertNotIn("example.invalid", str(ctx.exception))
        self.assertEqual(str(ctx.exception), "CLOUD_EXECUTOR_HTTP_403")

    def test_safe_configuration_error_is_preserved_for_diagnosis(self):
        body = json.dumps({"detail": "CLOUD_EXECUTOR_ISSUER_NOT_CONFIGURED"}).encode()
        error = HTTPError("https://example.invalid/attestation/challenge", 503, "Unavailable", {}, io.BytesIO(body))
        self.assertEqual(
            str(_safe_http_error(error)),
            "CLOUD_EXECUTOR_HTTP_503:CLOUD_EXECUTOR_ISSUER_NOT_CONFIGURED",
        )

    def test_safe_host_inventory_error_is_preserved_for_diagnosis(self):
        body = json.dumps({"detail": "CLOUD_EXECUTOR_HOST_BINDINGS_CONFIG_INVALID"}).encode()
        error = HTTPError("https://example.invalid/attestation/challenge", 503, "Unavailable", {}, io.BytesIO(body))
        self.assertEqual(
            str(_safe_http_error(error)),
            "CLOUD_EXECUTOR_HTTP_503:CLOUD_EXECUTOR_HOST_BINDINGS_CONFIG_INVALID",
        )

    def test_unknown_server_detail_is_not_echoed(self):
        private_like = "internal/path/with-secret-value"
        body = json.dumps({"detail": private_like}).encode()
        error = HTTPError("https://example.invalid/path", 503, "Unavailable", {}, io.BytesIO(body))
        self.assertEqual(str(_safe_http_error(error)), "CLOUD_EXECUTOR_HTTP_503")
        self.assertNotIn(private_like, str(_safe_http_error(error)))


if __name__ == "__main__":
    unittest.main()
