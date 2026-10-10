import unittest

from brain_v12.brain.github_auth import build_github_headers


class GitHubHeaderPolicyTests(unittest.TestCase):
    def test_public_read_mode_omits_authorization_without_token(self):
        headers = build_github_headers(None, require_token=False)
        self.assertNotIn("Authorization", headers)
        self.assertEqual(headers["Accept"], "application/vnd.github+json")

    def test_write_default_requires_token(self):
        with self.assertRaisesRegex(ValueError, "GITHUB_TOKEN_NOT_CONFIGURED"):
            build_github_headers(None)

    def test_configured_token_is_used(self):
        headers = build_github_headers("example-token")
        self.assertEqual(headers["Authorization"], "Bearer example-token")


if __name__ == "__main__":
    unittest.main()
