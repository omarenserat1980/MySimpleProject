import os
import unittest
from unittest.mock import patch

from brain_v12.brain.youtube_oauth import YouTubeOAuth


class EventStoreStub:
    def events(self, limit=200):
        return []


class YouTubeOAuthTests(unittest.TestCase):
    def setUp(self):
        self.oauth = YouTubeOAuth(EventStoreStub())

    def test_not_configured_without_client_credentials(self):
        with patch.dict(os.environ, {}, clear=True):
            snapshot = self.oauth.snapshot()
        self.assertFalse(snapshot["configured"])
        self.assertFalse(snapshot["ready_to_start"])
        self.assertFalse(snapshot["ready_to_store_token"])
        self.assertIn("YOUTUBE_CLIENT_ID", snapshot["missing_env"])

    def test_ready_to_start_with_client_and_redirect(self):
        env = {
            "YOUTUBE_CLIENT_ID": "client-id",
            "YOUTUBE_CLIENT_SECRET": "client-secret",
            "YOUTUBE_OAUTH_REDIRECT_URI": "https://example.test/api/youtube/oauth/callback",
            "YOUTUBE_TOKEN_ENCRYPTION_KEY": "unused-in-this-test",
        }
        with patch.dict(os.environ, env, clear=True):
            snapshot = self.oauth.snapshot()
        self.assertTrue(snapshot["configured"])
        self.assertTrue(snapshot["ready_to_start"])
        self.assertTrue(snapshot["ready_to_store_token"])
        self.assertFalse(snapshot["authorized"])

    def test_snapshot_reports_missing_encryption_key(self):
        env = {
            "YOUTUBE_CLIENT_ID": "client-id",
            "YOUTUBE_CLIENT_SECRET": "client-secret",
            "YOUTUBE_OAUTH_REDIRECT_URI": "https://example.test/callback",
        }
        with patch.dict(os.environ, env, clear=True):
            snapshot = self.oauth.snapshot()
        self.assertTrue(snapshot["configured"])
        self.assertTrue(snapshot["ready_to_start"])
        self.assertFalse(snapshot["ready_to_store_token"])
        self.assertIn("YOUTUBE_TOKEN_ENCRYPTION_KEY", snapshot["missing_env"])

if __name__ == "__main__":
    unittest.main()
