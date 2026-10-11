import io
import unittest
import urllib.error

from tools.request_cloud_executor_attestation import _safe_http_error


class CloudExecutorHttpDiagnosticTests(unittest.TestCase):
    def make_error(self, status, body):
        return urllib.error.HTTPError(
            url="https://control-plane.invalid/api/cloud-executor/attestation/challenge",
            code=status,
            msg="request failed",
            hdrs=None,
            fp=io.BytesIO(body),
        )

    def test_reports_auth_rejected_code_without_sensitive_values(self):
        err = self.make_error(403, b'{"detail":"CLOUD_EXECUTOR_AUTH_REJECTED"}')
        message = str(_safe_http_error(err))
        self.assertEqual(message, "CLOUD_EXECUTOR_HTTP_403:CLOUD_EXECUTOR_AUTH_REJECTED")
        self.assertNotIn("control-plane.invalid", message)

    def test_reports_host_binding_code(self):
        err = self.make_error(503, b'{"detail":"CLOUD_EXECUTOR_HOST_BINDING_REQUIRED"}')
        self.assertEqual(str(_safe_http_error(err)), "CLOUD_EXECUTOR_HTTP_503:CLOUD_EXECUTOR_HOST_BINDING_REQUIRED")

    def test_untrusted_error_detail_is_not_emitted(self):
        err = self.make_error(403, b'{"detail":"token=super-secret-value"}')
        self.assertEqual(str(_safe_http_error(err)), "CLOUD_EXECUTOR_HTTP_403")
        self.assertNotIn("super-secret-value", str(_safe_http_error(err)))

    def test_malformed_error_body_is_not_emitted(self):
        err = self.make_error(502, b"upstream body with internal information")
        self.assertEqual(str(_safe_http_error(err)), "CLOUD_EXECUTOR_HTTP_502")


if __name__ == "__main__":
    unittest.main()
