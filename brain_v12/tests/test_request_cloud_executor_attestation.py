import io
import unittest
import urllib.error
from unittest.mock import patch

from tools.request_cloud_executor_attestation import post


class CloudExecutorHttpDiagnosticTests(unittest.TestCase):
    def make_error(self, status, body):
        return urllib.error.HTTPError(
            url="https://control-plane.invalid/api/cloud-executor/attestation/challenge",
            code=status,
            msg="request failed",
            hdrs={"X-Debug": "do-not-log"},
            fp=io.BytesIO(body),
        )

    def call_with_error(self, error):
        with patch("tools.request_cloud_executor_attestation.urllib.request.urlopen", side_effect=error):
            with self.assertRaises(RuntimeError) as raised:
                post("https://control-plane.invalid", "/challenge", "super-secret-token", {})
        return raised.exception

    def test_allowlisted_auth_error_is_preserved(self):
        err = self.make_error(403, b'{"detail":"CLOUD_EXECUTOR_AUTH_REJECTED"}')
        self.assertEqual(str(self.call_with_error(err)), "CLOUD_EXECUTOR_HTTP_403:CLOUD_EXECUTOR_AUTH_REJECTED")

    def test_allowlisted_host_binding_error_is_preserved(self):
        err = self.make_error(503, b'{"detail":"CLOUD_EXECUTOR_HOST_BINDING_REQUIRED"}')
        self.assertEqual(str(self.call_with_error(err)), "CLOUD_EXECUTOR_HTTP_503:CLOUD_EXECUTOR_HOST_BINDING_REQUIRED")

    def test_arbitrary_uppercase_detail_is_redacted(self):
        err = self.make_error(403, b'{"detail":"SUPER_SECRET_INTERNAL_CODE"}')
        self.assertEqual(str(self.call_with_error(err)), "CLOUD_EXECUTOR_HTTP_403")

    def test_token_url_and_headers_are_not_chained_or_logged(self):
        err = self.make_error(403, b'{"detail":"token=super-secret-token"}')
        with patch("tools.request_cloud_executor_attestation.urllib.request.urlopen", side_effect=err):
            with self.assertRaises(RuntimeError) as raised:
                post("https://control-plane.invalid", "/challenge", "super-secret-token", {})
        self.assertIsNone(raised.exception.__cause__)
        self.assertNotIn("super-secret-token", str(raised.exception))
        self.assertNotIn("control-plane.invalid", str(raised.exception))

    def test_malformed_body_is_redacted(self):
        err = self.make_error(502, b"internal upstream body")
        self.assertEqual(str(self.call_with_error(err)), "CLOUD_EXECUTOR_HTTP_502")


if __name__ == "__main__":
    unittest.main()
