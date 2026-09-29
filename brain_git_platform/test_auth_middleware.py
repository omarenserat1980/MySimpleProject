import os
import unittest

from brain_git_platform.api.auth_middleware import require_scope


class AuthMiddlewareTests(unittest.TestCase):
    def test_missing_token_is_not_accepted(self):
        old = os.environ.pop("BRAIN_GIT_TOKEN", None)
        try:
            result = require_scope({}, "repo:read")
            self.assertFalse(result.ok)
            self.assertEqual(result.error, "authentication_not_configured")
        finally:
            if old is not None:
                os.environ["BRAIN_GIT_TOKEN"] = old

    def test_scoped_bearer_token(self):
        old_token = os.environ.get("BRAIN_GIT_TOKEN")
        old_scopes = os.environ.get("BRAIN_GIT_TOKEN_SCOPES")
        os.environ["BRAIN_GIT_TOKEN"] = "test-secret"
        os.environ["BRAIN_GIT_TOKEN_SCOPES"] = "repo:read"
        try:
            ok = require_scope({"Authorization": "Bearer test-secret"}, "repo:read")
            denied = require_scope({"Authorization": "Bearer test-secret"}, "repo:write")
            self.assertTrue(ok.ok)
            self.assertFalse(denied.ok)
        finally:
            if old_token is None:
                os.environ.pop("BRAIN_GIT_TOKEN", None)
            else:
                os.environ["BRAIN_GIT_TOKEN"] = old_token
            if old_scopes is None:
                os.environ.pop("BRAIN_GIT_TOKEN_SCOPES", None)
            else:
                os.environ["BRAIN_GIT_TOKEN_SCOPES"] = old_scopes


if __name__ == "__main__":
    unittest.main()
