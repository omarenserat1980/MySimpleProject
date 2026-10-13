import unittest
from unittest.mock import patch

from brain_v12.brain.render_cat_channel import RenderCatReadOnlyChannel


class RenderCatChannelTests(unittest.TestCase):
    def test_unconfigured_channel_fails_closed(self):
        with patch.dict("os.environ", {}, clear=True):
            channel = RenderCatReadOnlyChannel(base_url="", token="")
            result = channel.get("/health")
        self.assertEqual(result["status"], "NOT_CONFIGURED")
        self.assertFalse(result["ok"])

    def test_only_allowlisted_get_paths_are_exposed(self):
        channel = RenderCatReadOnlyChannel(base_url="https://render-cat.example")
        result = channel.get("/api/deploy")
        self.assertEqual(result["status"], "PATH_NOT_ALLOWED")
        self.assertFalse(result["ok"])

    def test_non_https_base_is_rejected_before_network(self):
        channel = RenderCatReadOnlyChannel(base_url="http://localhost:8787")
        result = channel.get("/health")
        self.assertEqual(result["status"], "INVALID_CONFIGURATION")
        self.assertFalse(result["ok"])

    def test_status_never_exposes_token(self):
        channel = RenderCatReadOnlyChannel(
            base_url="https://render-cat.example", token="never-display-this"
        )
        status = channel.status()
        self.assertTrue(status["credential_present"])
        self.assertNotIn("never-display-this", repr(status))
        self.assertFalse(status["credential_value_exposed"])


if __name__ == "__main__":
    unittest.main()
